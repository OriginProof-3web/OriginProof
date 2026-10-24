"""Owned W5 projection replay/process restart/reorg. No API operation rollback claim."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx


@contextmanager
def api_process(settings, out):
    """Run the unchanged candidate app in a new process with a private settings file."""
    config = out / f"projection-settings-{uuid4().hex}.json"
    with config.open("x") as stream:
        config.chmod(0o600)
        json.dump(settings.model_dump(mode="json"), stream)
    child_env = os.environ.copy()
    child_env.pop("OPENAI_API_KEY", None)
    child_env.update(LLM_PROVIDER="mock", OPENAI_MODEL="gpt-6-luna")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "serve",
                str(config),
                str(listener.fileno()),
            ],
            env=child_env,
            pass_fds=(listener.fileno(),),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            with httpx.Client(trust_env=False, timeout=1) as client:
                for _ in range(100):
                    assert process.poll() is None, "owned projection API exited"
                    try:
                        if client.get(url + "/health/live").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("owned projection API startup timeout")
            yield url, process.pid
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            assert process.poll() is not None, "owned API process did not close"


async def exercise(settings, prepared, helper, out):
    from infrastructure.blockchain.reader import digest
    from originproof_api.chain_management import ChainManagement
    from originproof_api.database import AuditEventRow, Database, OperationRow
    from originproof_indexer.projection import (
        ProjectionStore,
        checkpoints,
        decode_proof_log,
        events,
        processed_blocks,
        proof_events,
    )
    from sqlalchemy import func, select

    database = Database(settings.database_url)
    manager = ChainManagement(database, settings)
    manifest = manager.manifest
    store = ProjectionStore(database.engine.sync_engine)
    rpc_url = settings.blockchain_rpc_url
    chain, deployment = manifest.chain_id, manifest.deployment_id
    proof = prepared["issuers"]["bank"]["historical_proof_id"]
    proof_hash = "0x" + digest(proof).hex()
    projection_tables = (events, proof_events, processed_blocks, checkpoints)

    async def store_call(action):
        async with database.engine.connect() as connection:
            return await connection.run_sync(lambda _: action())

    async def table_counts():
        async with database.engine.connect() as connection:
            return {
                table.name: await connection.scalar(select(func.count()).select_from(table))
                for table in projection_tables
            }

    async def application_counts():
        async with database.session_factory() as db:
            return [
                await db.scalar(select(func.count()).select_from(table))
                for table in (OperationRow, AuditEventRow)
            ]

    async def number():
        return int(await helper.rpc(rpc_url, "eth_blockNumber", []), 16)

    async def block(n):
        return await helper.rpc(rpc_url, "eth_getBlockByNumber", [hex(n), False])

    async def login(client):
        response = await client.post(
            "/v1/auth/login",
            json={k: prepared["accounts"]["operator"][k] for k in ("username", "password")},
        )
        assert response.status_code == 200
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]

    async def sync(client, target=None, status="SYNCED"):
        for _ in range(150):
            response = await client.get("/v1/chain-sync")
            assert response.status_code == 200
            view = response.json()
            if view["status"] == status and (target is None or view["checkpoint_block"] == target):
                if status == "SYNCED":
                    actual = await block(view["checkpoint_block"])
                    assert actual["hash"].lower() == view["checkpoint_hash"]
                    assert view["authority"] == "HISTORICAL_EVENTS_ONLY"
                return view
            await asyncio.sleep(0.2)
        raise AssertionError("projection did not reach expected checkpoint/status")

    async def active(client):
        for role in ("bank", "office"):
            target = prepared["issuers"][role]["historical_proof_id"]
            response = await client.post(
                f"/v2/proofs/{target}/verify",
                json={"request_id": f"req_w5_projection_{uuid4().hex}"},
            )
            assert response.status_code == 200
            view = response.json()
            assert (view["verification_status"], view["lifecycle_status"]) == ("VERIFIED", "ACTIVE")

    try:
        await helper.rpc(rpc_url, "evm_mine", [])
        target = await number() - 1
        with api_process(settings, out) as (url, first_pid):
            async with httpx.AsyncClient(base_url=url, trust_env=False, timeout=30) as client:
                await login(client)
                initial = await sync(client, target)
                await active(client)
                before = await table_counts()
                raw = await helper.rpc(
                    rpc_url,
                    "eth_getLogs",
                    [
                        {
                            "address": manifest.contract("ProofStatusRegistry").address,
                            "fromBlock": hex(target),
                            "toBlock": hex(target),
                        }
                    ],
                )
                decoded = [decode_proof_log(item, chain, deployment) for item in raw]
                replay = await store_call(
                    lambda: store.apply_block(
                        chain, deployment, target, initial["checkpoint_hash"], decoded
                    )
                )
                assert replay is False and await table_counts() == before
        with api_process(settings, out) as (url, second_pid):
            assert first_pid != second_pid
            async with httpx.AsyncClient(base_url=url, trust_env=False, timeout=30) as client:
                await login(client)
                await sync(client, target)
                assert await table_counts() == before
                await active(client)
                await helper.rpc(rpc_url, "evm_mine", [])
                ancestor = await number() - 1
                await sync(client, ancestor)
                # Snapshot includes an already tracked canonical ancestor, plus one tip block.
                snap = await helper.rpc(rpc_url, "evm_snapshot", [])
                snapshot_tip = await number()
                original_app_counts = await application_counts()
                transaction = await manager.writer.prepare_revoke_proof(
                    manifest.roles["issuer_account"], proof
                )
                submitted = await manager.writer.submit_prepared(transaction)
                assert submitted.tx_hash is not None
                outcome = await manager.writer.confirm_prepared(transaction, submitted.tx_hash)
                assert outcome.state.value == "CONFIRMED"
                receipt = await helper.rpc(rpc_url, "eth_getTransactionReceipt", [outcome.tx_hash])
                assert int(receipt["status"], 16) == 1
                orphan_block = int(receipt["blockNumber"], 16)
                await helper.rpc(rpc_url, "evm_mine", [])
                await sync(client, orphan_block)
                assert (
                    await store_call(
                        lambda: store.projected_proof_status(chain, deployment, proof_hash)
                    )
                    == "REVOKED"
                )
                assert await helper.rpc(rpc_url, "evm_revert", [snap]) is True
                await sync(client, status="RECOVERING")
                # Tip rollback is held pending; create a distinct sufficiently confirmed fork.
                original_tip = await block(snapshot_tip)
                await helper.rpc(
                    rpc_url, "evm_setNextBlockTimestamp", [int(original_tip["timestamp"], 16) + 30]
                )
                while await number() <= orphan_block:
                    await helper.rpc(rpc_url, "evm_mine", [])
                canonical = await block(orphan_block)
                assert canonical["hash"] != receipt["blockHash"]
                recovered = await sync(client, orphan_block)
                assert recovered["checkpoint_hash"] == canonical["hash"].lower()
                assert (
                    await store_call(
                        lambda: store.projected_proof_status(chain, deployment, proof_hash)
                    )
                    == "ACTIVE"
                )
                async with database.engine.connect() as connection:
                    orphan_events = await connection.scalar(
                        select(func.count())
                        .select_from(events)
                        .where(events.c.block_hash == receipt["blockHash"].lower())
                    )
                    orphan_proof_events = await connection.scalar(
                        select(func.count())
                        .select_from(proof_events)
                        .where(
                            proof_events.c.proof_id_hash == proof_hash,
                            proof_events.c.event_type == "REVOKED",
                        )
                    )
                assert orphan_events == 0 and orphan_proof_events == 0
                assert await application_counts() == original_app_counts
                await active(client)
        return {
            "poll_seconds": settings.projection_poll_seconds,
            "layer": "actual PostgreSQL/Anvil and socket HTTP with separate API process",
            "replay_returned": False,
            "replay_table_counts_unchanged": True,
            "api_pid_changed": True,
            "persisted_checkpoint_and_counts_preserved": True,
            "continued_checkpoint": ancestor,
            "reorg": {
                "orphan_block": orphan_block,
                "orphan_hash": receipt["blockHash"],
                "canonical_hash": canonical["hash"],
                "tip_rollback": "RECOVERING",
                "recovered_checkpoint": recovered["checkpoint_block"],
                "orphan_events_removed": True,
                "historical_status": "ACTIVE",
                "two_proofs_canonical_reader": "VERIFIED/ACTIVE",
                "scope": "direct issuer gateway revoke; no API Operation/Audit rollback claim",
                "application_counts_unchanged": True,
            },
            "owned_api_processes_closed": True,
        }
    finally:
        await database.dispose()


def run(settings, prepared, helper, env_stack, out):
    del env_stack  # Only passed owned settings RPC/DB; never discovers shared resources.
    configured = settings.model_copy(
        update={
            "projection_enabled": True,
            "projection_poll_seconds": 1,
            "blockchain_issuer_id": settings.finals_payment_issuer_id,
        }
    )
    return asyncio.run(exercise(configured, prepared, helper, out))


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "serve":
        raise SystemExit("import run() from owned W5 QA runner")
    import uvicorn
    from originproof_api.main import create_app
    from originproof_api.settings import Settings

    config = Settings(_env_file=None, **json.loads(Path(sys.argv[2]).read_text()))
    listener = socket.socket(fileno=int(sys.argv[3]))
    uvicorn.Server(
        uvicorn.Config(
            create_app(settings=config),
            log_level="critical",
            access_log=False,
            proxy_headers=False,
        )
    ).run(sockets=[listener])
