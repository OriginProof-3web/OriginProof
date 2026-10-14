"""Prepare owned W4 D3 accounts/data and read-only evidence, not browser acceptance."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import secrets
import socket
import threading
import time
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn
from infrastructure.blockchain.reader import digest
from originproof_api.accounts import password_hash
from originproof_api.chain_management import ChainManagement
from originproof_api.database import (
    AccountRow,
    AuditEventRow,
    Database,
    FinalsProofRow,
    IssuerKeyRow,
    OperationRow,
)
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_core.ports import DependencyUnavailableError
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[2]


def private_json(path: Path, value) -> None:
    # Exclusive creation preserves earlier runs; credentials never go to stdout.
    with path.open("x", encoding="utf-8") as stream:
        path.chmod(0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
        stream.write("\n")


def qa_module():
    spec = importlib.util.spec_from_file_location(
        "w4_lifecycle_qa", ROOT / "fixtures/finals/test_w4_lifecycle_qa.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def seed(settings: Settings, api_url: str) -> dict:
    suffix = uuid4().hex[:10]
    accounts = {
        role: {
            "username": f"w4_{role}_{suffix}",
            "account_id": f"acct_w4_{role}_{suffix}",
            "password": secrets.token_urlsafe(24),
            "role": "issuer"
            if role in ("bank", "office")
            else "recipient"
            if role == "other_recipient"
            else role,
            "issuer_id": getattr(settings, f"finals_{profile}_issuer_id")
            if role in ("bank", "office")
            else None,
        }
        for role, profile in (
            ("operator", ""),
            ("bank", "payment"),
            ("office", "document"),
            ("recipient", ""),
            ("other_recipient", ""),
        )
    }
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as db:
            db.add_all(
                [
                    AccountRow(
                        **{k: v for k, v in account.items() if k != "password"},
                        password_hash=password_hash(account["password"]),
                    )
                    for account in accounts.values()
                ]
            )
            await db.commit()
    finally:
        await database.dispose()
    now = datetime.now(UTC).replace(microsecond=0)
    key_input = {
        "reason": "Synthetic W4 D3 preparation",
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(days=14)).isoformat(),
    }
    prepared = {"accounts": accounts, "issuers": {}}
    async with AsyncExitStack() as stack:
        clients = {}
        for role, account in accounts.items():
            client = await stack.enter_async_context(
                httpx.AsyncClient(base_url=api_url, timeout=30, trust_env=False)
            )
            response = await client.post(
                "/v1/auth/login", json={k: account[k] for k in ("username", "password")}
            )
            if response.status_code != 200:
                raise RuntimeError("preparation login failed")
            client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
            clients[role] = client
        for role in ("bank", "office"):
            client = clients[role]
            response = await client.post(
                "/v1/issuer-applications", json={"issuer_name": f"Synthetic W4 D3 {role}"}
            )
            if response.status_code != 201:
                raise RuntimeError("preparation application failed")
            target = f"/v1/operator/issuer-applications/{response.json()['application_id']}"
            response = await clients["operator"].post(
                target + "/decision", json={"decision": "APPROVE", "reason": "synthetic"}
            )
            if response.status_code != 200:
                raise RuntimeError("preparation approval failed")
            for path, body in (
                (
                    target + "/activate",
                    {"request_id": f"req_d3_seed_activate_{role}", "reason": "synthetic"},
                ),
                ("/v1/issuer/keys", key_input | {"request_id": f"req_d3_seed_key_{role}"}),
            ):
                response = await (
                    clients["operator"] if path == target + "/activate" else client
                ).post(path, json=body)
                if response.status_code != 200 or response.json()["status"] != "CONFIRMED":
                    raise RuntimeError("preparation chain operation unconfirmed")
            old_key = response.json()["target_id"]
            content = (
                {
                    "proof_type": "PAYMENT_REQUEST",
                    "amount_minor": 10000,
                    "currency": "KRW",
                    "target_ref": f"SYNTHETIC-W4-D3-{suffix}",
                }
                if role == "bank"
                else {
                    "proof_type": "OFFICIAL_DOCUMENT",
                    "institution_code": "ORIGIN_MOCK_OFFICE",
                    "document_type": "Certificate",
                    "document_number": f"SYNTHETIC-W4-D3-{suffix}",
                    "version": 1,
                }
            )
            issue = {
                "request_id": f"req_d3_seed_proof_{role}",
                "recipient_id": accounts["recipient"]["account_id"],
                "expires_at": (now + timedelta(days=7)).isoformat(),
                "content": content,
            }
            response = await client.post("/v2/issuer/proofs", json=issue)
            if response.status_code != 200 or response.json()["registration_status"] != "CONFIRMED":
                raise RuntimeError("preparation historical Proof unconfirmed")
            prepared["issuers"][role] = {
                "old_key_id": old_key,
                "historical_proof_id": response.json()["proof_id"],
                "rotation_input": key_input | {"request_id": f"req_d3_ui_rotate_{role}"},
                "new_issue_input": issue | {"request_id": f"req_d3_ui_new_{role}"},
                "consume_issue_input": issue | {"request_id": f"req_d3_ui_consume_{role}"},
            }
            # Fresh anonymous socket request is an initial-state check, not a UI action.
            async with httpx.AsyncClient(base_url=api_url, trust_env=False) as public:
                result = await public.post(
                    f"/v2/proofs/{response.json()['proof_id']}/verify",
                    json={"request_id": "req_d3_seed_verify"},
                )
                if result.status_code != 200 or (
                    result.json()["verification_status"],
                    result.json()["lifecycle_status"],
                ) != ("VERIFIED", "ACTIVE"):
                    raise RuntimeError("preparation historical Proof is not ACTIVE")
        for client in clients.values():
            await client.post("/v1/auth/logout")
    return prepared


async def snapshot(settings: Settings, helper) -> dict:
    """Whitelist DB/chain evidence; never serialize envelopes or recovery secrets."""
    database = Database(settings.database_url)
    manager = ChainManagement(database, settings)
    try:
        async with database.session_factory() as db:
            proofs = list(await db.scalars(select(FinalsProofRow)))
            operations = list(await db.scalars(select(OperationRow)))
            keys = list(await db.scalars(select(IssuerKeyRow)))
            result = {
                "observed_at": datetime.now(UTC).isoformat(),
                "deployment_id": manager.manifest.deployment_id,
                "chain_id": manager.manifest.chain_id,
                "audit_count": await db.scalar(select(func.count()).select_from(AuditEventRow)),
                "keys": [
                    {k: getattr(row, k) for k in ("key_id", "issuer_id", "status", "selected")}
                    for row in keys
                ],
                "operations": [
                    {
                        k: getattr(row, k)
                        for k in (
                            "operation_id",
                            "action",
                            "request_id",
                            "status",
                            "tx_hash",
                            "target_id",
                        )
                    }
                    for row in operations
                ],
                "proofs": [],
            }
        for proof in proofs:
            state, events, chain_error = None, None, None
            try:
                state = await manager.reader(proof.issuer_id).get_proof_state(
                    proof.proof_id, datetime.now(UTC)
                )
                events = await helper.rpc(
                    settings.blockchain_rpc_url,
                    "eth_getLogs",
                    [
                        {
                            "address": manager.manifest.contract("ProofStatusRegistry").address,
                            "fromBlock": "0x0",
                            "toBlock": "latest",
                            "topics": [None, "0x" + digest(proof.proof_id).hex()],
                        }
                    ],
                )
            except (DependencyUnavailableError, httpx.HTTPError, AssertionError):
                chain_error = "DEPENDENCY_UNAVAILABLE"
            result["proofs"].append(
                {
                    "proof_id": proof.proof_id,
                    "issuer_id": proof.issuer_id,
                    "key_id": proof.key_id,
                    "db_key_id_hash": "0x" + digest(proof.key_id).hex(),
                    "proof_type": proof.envelope["proof_type"],
                    "chain_error": chain_error,
                    "chain": None
                    if state is None
                    else {
                        k: getattr(state, k)
                        for k in (
                            "key_id_hash",
                            "block_number",
                            "block_hash",
                            "status",
                            "single_use",
                            "consumable_at",
                            "revoked_at",
                            "consumed_at",
                        )
                    },
                    "events": None
                    if events is None
                    else [
                        {k: event[k] for k in ("transactionHash", "blockHash", "logIndex")}
                        | {"topic": event["topics"][0]}
                        for event in events
                    ],
                }
            )
        for operation in result["operations"]:
            if operation["tx_hash"]:
                try:
                    receipt = await helper.rpc(
                        settings.blockchain_rpc_url,
                        "eth_getTransactionReceipt",
                        [operation["tx_hash"]],
                    )
                    operation["receipt_status"] = None if receipt is None else receipt["status"]
                except (httpx.HTTPError, AssertionError):
                    operation["receipt_status"] = None
                    operation["receipt_error"] = "DEPENDENCY_UNAVAILABLE"
        return result
    finally:
        await database.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="hold owned API/DB/chain for UI QA")
    args = parser.parse_args()
    if os.getenv("W4_D3_PREPARE") != "1":
        parser.error("W4_D3_PREPARE=1 is required for disposable provisioning")
    out = ROOT / "build/w4-d3" / uuid4().hex
    out.mkdir(parents=True, mode=0o700)
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["OPENAI_MODEL"] = "gpt-6-luna"
    os.environ.pop("OPENAI_API_KEY", None)
    helper = qa_module()
    # Keep the existing pinned deployment consistent with the API/Contract source.
    helper.command(
        [
            "git",
            "diff",
            "--quiet",
            helper.PRODUCT_SHA,
            "--",
            "apps/api",
            "packages/python",
            "packages/contracts",
            "infra/docker/deployer.Dockerfile",
        ]
    )
    resources = helper.disposable_stack.__wrapped__(out)
    server = thread = None
    summary = {"d3_browser": "NOT_RUN", "prepared": False, "resources_closed": False}
    try:
        env = next(resources)
        suffix = uuid4().hex[:10]
        settings = Settings(
            _env_file=None,
            database_url=env["database_url"],
            blockchain_rpc_url=env["rpc_url"],
            blockchain_manifest_path=env["manifest"],
            signer_directory=str(out / "signers"),
            session_cookie_secure=False,
            blockchain_chain_id=31337,
            finals_payment_issuer_id=f"iss_d3_bank_{suffix}",
            finals_document_issuer_id=f"iss_d3_office_{suffix}",
            finals_document_institution_code="ORIGIN_MOCK_OFFICE",
        )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            api_url = f"http://127.0.0.1:{listener.getsockname()[1]}"
            server = uvicorn.Server(
                uvicorn.Config(
                    create_app(settings=settings),
                    log_level="critical",
                    access_log=False,
                )
            )
            thread = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            thread.start()
            for _ in range(100):
                if server.started:
                    break
                if not thread.is_alive():
                    raise RuntimeError("owned API startup failed")
                time.sleep(0.1)
            else:
                raise RuntimeError("owned API startup timed out")
            prepared = asyncio.run(seed(settings, api_url))
            private_json(out / "accounts.json", prepared["accounts"])
            private_json(out / "inputs.json", prepared["issuers"])
            private_json(
                out / "session.json",
                {
                    "api_url": api_url,
                    "owned_anvil_container": env["anvil"],
                    "product_sha": helper.PRODUCT_SHA,
                    "scope": "owned disposable resources; credentials are in private accounts.json",
                },
            )
            baseline = asyncio.run(snapshot(settings, helper))
            if (
                len(baseline["proofs"]) != 2
                or len(baseline["keys"]) != 2
                or not all(key["selected"] for key in baseline["keys"])
                or not all(
                    proof["chain"]["status"] == "ACTIVE"
                    and proof["chain"]["key_id_hash"] == proof["db_key_id_hash"]
                    and len(proof["events"]) == 1
                    for proof in baseline["proofs"]
                )
                or not all(
                    op["status"] == "CONFIRMED" and op["receipt_status"] == "0x1"
                    for op in baseline["operations"]
                )
            ):
                raise RuntimeError("preparation DB/chain baseline mismatch")
            private_json(out / "baseline.json", baseline)
            cases = json.loads((ROOT / "fixtures/finals/w4_d3_cases.json").read_text())
            private_json(
                out / "results.json",
                {
                    "cases": [
                        {"id": case["id"], "status": "NOT_RUN", "evidence": []}
                        for case in cases["cases"]
                    ],
                },
            )
            summary.update(
                prepared=True,
                accounts=5,
                issuers=2,
                historical_proofs=2,
                initial_http_verdicts="2 VERIFIED + ACTIVE",
                cases=len(cases["cases"]),
            )
            print(f"Prepared owned D3 resources. API: {api_url}; private files: {out}", flush=True)
            if args.serve:
                print(
                    "UI QA: enter 'snapshot' for read-only evidence or 'stop' to clean up.",
                    flush=True,
                )
                while True:
                    action = input().strip()
                    if action == "stop":
                        break
                    if action == "snapshot":
                        path = out / f"snapshot-{uuid4().hex}.json"
                        private_json(path, asyncio.run(snapshot(settings, helper)))
                        print(f"Read-only evidence: {path}", flush=True)
    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as error:
        summary["error_type"] = type(error).__name__
        print(f"Preparation failed ({type(error).__name__}); diagnostics stay private.", flush=True)
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=15)
        resources.close()
        summary["resources_closed"] = thread is None or not thread.is_alive()
        private_json(out / "summary.json", summary)
    return 0 if summary["prepared"] and summary["resources_closed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
