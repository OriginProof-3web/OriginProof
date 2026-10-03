"""D policy vectors plus opt-in ASGI/real PostgreSQL/Anvil QA; no browser claim."""

import asyncio
import json
import os
import secrets
import subprocess
import sys
import time
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from infrastructure.blockchain.reader import digest
from infrastructure.blockchain.writer import ChainOperationState
from originproof_api import chain_management, finals_proofs
from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, AuditEventRow, Database, OperationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_core import (
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
    LifecycleStatus,
)
from originproof_core.finals import FinalsSignedProofEnvelope
from originproof_core.finals_verification import evaluate_finals
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SHA = "8011f7fe3da033c9253894a9de0fd98aa7bbcc16"
DEPLOYER = "originproof-w4-d-qa-deployer:8011f7f"
FOUNDRY = (
    "ghcr.io/foundry-rs/foundry:v1.4.4@sha256:"
    "9584dfbb0e2e9bda80332b66a7cebed635fc9786638871df6b7594e39e678578"
)
MANIFEST = json.loads((ROOT / "fixtures/finals/w4_cases.json").read_text())


POLICY_CASES = [
    (profile, case)
    for case in MANIFEST["cases"]
    for profile in case.get("profiles", MANIFEST["profiles"])
]


@pytest.mark.parametrize(
    ("profile", "case"),
    POLICY_CASES,
    ids=[f"{profile}:{case['id']}" for profile, case in POLICY_CASES],
)
def test_w4_policy(profile, case):
    data = json.loads((ROOT / f"fixtures/golden/{profile}_signing_v2.json").read_text())
    envelope = FinalsSignedProofEnvelope.model_validate(data["envelope"])
    now = envelope.issued_at + timedelta(seconds=120)
    if "expiry_offset" in case:
        now = envelope.expires_at + timedelta(seconds=case["expiry_offset"])
    key_until = (
        envelope.issued_at + timedelta(seconds=60)
        if case.get("historical_key_expired")
        else envelope.expires_at
    )
    if case.get("invalid_signature"):
        envelope = envelope.model_copy(update={"signature": "0x" + "00" * 65})
    result = evaluate_finals(
        envelope,
        request_id="req_w4_d_policy",
        chain_id=envelope.chain_id,
        issuer=IssuerRecord(
            issuer_id=envelope.issuer_id,
            status=IssuerTrustStatus(case.get("issuer_status", "ACTIVE")),
        ),
        key=KeyRecord(
            key_id=envelope.key_id,
            issuer_id=envelope.issuer_id,
            signer=data["signer"],
            status=KeyTrustStatus(case.get("key_status", "ACTIVE")),
            valid_from=envelope.issued_at,
            valid_until=key_until,
        ),
        proof_states={LifecycleStatus(value) for value in case.get("proof_states", ["ACTIVE"])},
        now=now,
    )
    assert result.verification_status == case.get("verification", "VERIFIED")
    assert result.lifecycle_status == case["lifecycle"]
    assert set(result.reason_codes) == set(case["reasons"])
    assert result.checks["signature"] == ("FAIL" if case.get("invalid_signature") else "PASS")


def command(args, *, env=None, timeout=180):
    """Keep captured Docker/DB diagnostics private, including generated credentials."""
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"QA command failed: {args[0]} (exit {result.returncode})")
    return result.stdout.decode().strip()


class QAStack(dict):
    def __repr__(self):
        return "<new disposable W4 DB/Anvil; credentials omitted>"


@pytest.fixture
def disposable_stack(tmp_path):
    # Only this fixture creates endpoints; accepting a caller's DB/RPC is unnecessary.
    tmp_path.chmod(0o700)
    label = json.loads(command(["docker", "image", "inspect", DEPLOYER]))[0]["Config"]["Labels"]
    assert label.get("org.opencontainers.image.revision") == PRODUCT_SHA
    prefix = f"originproof-w4-d-qa-{uuid4().hex[:12]}"
    postgres, anvil = f"{prefix}-pg", f"{prefix}-anvil"
    names = []
    network_created = False
    env_file = tmp_path / "postgres.env"
    password = secrets.token_hex(24)
    env_file.write_text(
        f"POSTGRES_USER=originproof\nPOSTGRES_PASSWORD={password}\n"
        "POSTGRES_DB=originproof_w4_d_qa\n"
    )
    env_file.chmod(0o600)
    try:
        command(["docker", "network", "create", prefix])
        network_created = True
        command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                postgres,
                "--network",
                prefix,
                "--env-file",
                str(env_file),
                "--tmpfs",
                "/var/lib/postgresql/data",
                "-p",
                "127.0.0.1::5432",
                "postgres:16.4-alpine",
            ]
        )
        names.append(postgres)
        command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                anvil,
                "--network",
                prefix,
                "--network-alias",
                "anvil",
                "-p",
                "127.0.0.1::8545",
                "--entrypoint",
                "anvil",
                FOUNDRY,
                "--host",
                "0.0.0.0",
                "--chain-id",
                "31337",
                "--state",
                "/tmp/w4-state.json",
                "--preserve-historical-states",
            ]
        )
        names.append(anvil)
        for _ in range(80):
            ready = subprocess.run(
                ["docker", "exec", postgres, "pg_isready", "-U", "originproof"],
                capture_output=True,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("QA PostgreSQL not ready")
        pg_port = command(["docker", "port", postgres, "5432/tcp"]).split(":")[-1]
        rpc_port = command(["docker", "port", anvil, "8545/tcp"]).split(":")[-1]
        database_url = (
            f"postgresql+asyncpg://originproof:{password}@127.0.0.1:{pg_port}/originproof_w4_d_qa"
        )
        rpc_url = f"http://127.0.0.1:{rpc_port}"
        golden = json.loads((ROOT / "fixtures/golden/payment_request_signing_v2.json").read_text())
        deploy_dir = tmp_path / "deployments"
        deploy_dir.mkdir()
        command(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                prefix,
                "-v",
                f"{deploy_dir}:/workspace/packages/contracts/deployments",
                DEPLOYER,
                "uv",
                "run",
                "--package",
                "originproof-api",
                "python",
                "packages/contracts/script/deploy_local.py",
                "--rpc-url",
                "http://anvil:8545",
                "--signer",
                golden["signer"],
                "--source-commit-sha",
                PRODUCT_SHA,
            ]
        )
        env = os.environ | {"API_DATABASE_URL": database_url}
        env.pop("OPENAI_API_KEY", None)
        command(
            [sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
            env=env,
        )
        yield QAStack(
            {
                "database_url": database_url,
                "rpc_url": rpc_url,
                "manifest": str(deploy_dir / "31337.local.json"),
                "directory": tmp_path,
                "anvil": anvil,
            }
        )
    finally:
        # Generated names are the only resources this fixture can remove.
        for name in reversed(names):
            command(["docker", "rm", "-f", name])
        if network_created:
            command(["docker", "network", "rm", prefix])


async def rpc(url, method, params):
    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        body = (
            await client.post(
                url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params,
                },
            )
        ).json()
    assert "error" not in body
    return body["result"]


@pytest.mark.skipif(
    os.getenv("W4_LIVE_QA") != "1" or os.getenv("W4_QA_DISPOSABLE") != "1",
    reason="explicit W4 disposable Docker opt-in required",
)
async def test_w4_real_database_and_chain(disposable_stack, monkeypatch):
    env = disposable_stack
    suffix = uuid4().hex[:10]
    clock = [datetime.now(UTC).replace(microsecond=0)]

    class ControlledClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0].astimezone(tz) if tz else clock[0].replace(tzinfo=None)

    # Only trusted API clock inputs are controlled. Reader/Writer/EVM state is real.
    monkeypatch.setattr(finals_proofs, "datetime", ControlledClock)
    monkeypatch.setattr(chain_management, "datetime", ControlledClock)
    settings = Settings(
        _env_file=None,
        database_url=env["database_url"],
        blockchain_rpc_url=env["rpc_url"],
        blockchain_manifest_path=env["manifest"],
        signer_directory=str(env["directory"] / "signers"),
        finals_payment_issuer_id=f"iss_bank_{suffix}",
        finals_document_issuer_id=f"iss_office_{suffix}",
    )
    database = Database(settings.database_url)
    app = create_app(database=database, settings=settings)
    password = secrets.token_urlsafe(24)
    roles = ("operator", "bank", "office", "recipient", "other_recipient")
    accounts = {
        role: AccountRow(
            account_id=f"acct_{role}_{suffix}",
            username=f"{role}_{suffix}",
            password_hash=password_hash(password),
            role="issuer"
            if role in ("bank", "office")
            else "recipient"
            if role == "other_recipient"
            else role,
            issuer_id=f"iss_{role}_{suffix}" if role in ("bank", "office") else None,
        )
        for role in roles
    }
    try:
        async with database.session_factory() as db:
            db.add_all(accounts.values())
            await db.commit()
        async with AsyncExitStack() as stack:
            clients = {}
            for role in (*roles, "anonymous"):
                client = await stack.enter_async_context(
                    httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app),
                        base_url="http://test",
                    )
                )
                clients[role] = client
                if role != "anonymous":
                    login = await client.post(
                        "/v1/auth/login",
                        json={
                            "username": accounts[role].username,
                            "password": password,
                        },
                    )
                    assert login.status_code == 200
                    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
            admin, bank, office, recipient, other, public = clients.values()
            origin = clock[0]
            key_input = {
                "reason": "synthetic W4 QA",
                "valid_from": (origin - timedelta(minutes=10)).isoformat(),
                "valid_until": (origin + timedelta(seconds=120)).isoformat(),
            }
            for role in ("bank", "office"):
                application = await clients[role].post(
                    "/v1/issuer-applications", json={"issuer_name": f"Synthetic W4 {role}"}
                )
                assert application.status_code == 201
                application_id = application.json()["application_id"]
                decision = await admin.post(
                    f"/v1/operator/issuer-applications/{application_id}/decision",
                    json={"decision": "APPROVE", "reason": "synthetic"},
                )
                assert decision.status_code == 200
                activated = await admin.post(
                    f"/v1/operator/issuer-applications/{application_id}/activate",
                    json={"request_id": f"req_activate_{role}", "reason": "synthetic"},
                )
                assert activated.json()["status"] == "CONFIRMED"
                registered = await clients[role].post(
                    "/v1/issuer/keys", json=key_input | {"request_id": f"req_key_{role}"}
                )
                assert registered.json()["status"] == "CONFIRMED"
            manager = app.state.chain_management

            async def issue(role, label, *, lifetime=3600):
                content = (
                    {
                        "proof_type": "PAYMENT_REQUEST",
                        "amount_minor": 10000,
                        "currency": "KRW",
                        "target_ref": f"synthetic {label}",
                    }
                    if role == "bank"
                    else {
                        "proof_type": "OFFICIAL_DOCUMENT",
                        "institution_code": "ORIGIN_MOCK_OFFICE",
                        "document_type": "Certificate",
                        "document_number": f"SYNTHETIC-{label}",
                        "version": 1,
                    }
                )
                response = await clients[role].post(
                    "/v2/issuer/proofs",
                    json={
                        "request_id": f"req_{role}_{label}",
                        "recipient_id": accounts["recipient"].account_id,
                        "expires_at": (clock[0] + timedelta(seconds=lifetime)).isoformat(),
                        "content": content,
                    },
                )
                assert response.status_code == 200
                assert response.json()["registration_status"] == "CONFIRMED"
                return response.json()

            async def verify(proof, lifecycle="ACTIVE", reasons=()):
                response = await public.post(
                    f"/v2/proofs/{proof['proof_id']}/verify", json={"request_id": "req_verify"}
                )
                assert response.status_code == 200
                result = response.json()
                assert result["verification_status"] == "VERIFIED"
                assert result["lifecycle_status"] == lifecycle
                assert result["checks"]["signature"] == "PASS"
                assert result["checks"]["proof_status"] == "PASS"
                assert set(result["reason_codes"]) == set(reasons)
                return result

            async def events(proof):
                return await rpc(
                    env["rpc_url"],
                    "eth_getLogs",
                    [
                        {
                            "address": manager.manifest.contract("ProofStatusRegistry").address,
                            "fromBlock": "0x0",
                            "toBlock": "latest",
                            "topics": [None, "0x" + digest(proof["proof_id"]).hex()],
                        }
                    ],
                )

            histories = {role: await issue(role, "history") for role in ("bank", "office")}
            payment = await issue("bank", "race")
            document = await issue("office", "readonly")
            before_events = await events(payment)
            async with database.session_factory() as db:
                before_counts = [
                    await db.scalar(select(func.count()).select_from(model))
                    for model in (OperationRow, AuditEventRow)
                ]
            for _ in range(3):
                await verify(payment)
                await verify(document)
                assert (await public.get(f"/v2/proofs/{payment['proof_id']}")).status_code == 200
            use = f"/v2/proofs/{payment['proof_id']}/consume"
            for client, expected in ((public, 401), (admin, 404), (office, 404), (other, 404)):
                assert (
                    await client.post(use, json={"request_id": "req_denied"})
                ).status_code == expected
            assert (
                await recipient.post(
                    use, json={"request_id": "req_csrf"}, headers={"X-CSRF-Token": "wrong"}
                )
            ).status_code == 403
            for injected in (
                {"actor_kind": 0},
                {"actor_binding": "0x" + "ff" * 32},
                {"account_id": accounts["bank"].account_id},
            ):
                assert (
                    await recipient.post(use, json={"request_id": "req_injected"} | injected)
                ).status_code == 422
            denied_doc = await recipient.post(
                f"/v2/proofs/{document['proof_id']}/consume", json={"request_id": "req_document"}
            )
            assert (
                denied_doc.status_code == 409
                and denied_doc.json()["detail"] == "PROOF_NOT_SINGLE_USE"
            )
            async with database.session_factory() as db:
                assert bool(
                    before_counts
                    == [
                        await db.scalar(select(func.count()).select_from(model))
                        for model in (OperationRow, AuditEventRow)
                    ]
                )
            assert bool(await events(payment) == before_events)
            for client, expected in ((public, 401), (recipient, 403), (admin, 403), (office, 404)):
                denied = await client.post(
                    f"/v2/issuer/proofs/{payment['proof_id']}/revoke",
                    json={"request_id": "req_denied_revoke", "reason": "synthetic"},
                )
                assert denied.status_code == expected

            # Direct non-gateway sender and wrong recipient commitment reach the real EVM.
            from originproof_api.database import FinalsProofRow

            async with database.session_factory() as db:
                binding = (await db.get(FinalsProofRow, payment["proof_id"])).envelope[
                    "subject_binding_hash"
                ]
            for sender, actor in (
                (manager.manifest.roles["registry_admin"], binding),
                (manager.manifest.roles["gateway"], "0x" + "ff" * 32),
            ):
                prepared = await manager.writer.prepare_consume_proof(
                    sender, payment["proof_id"], 1, actor
                )
                submitted = await manager.writer.submit_prepared(prepared)
                assert submitted.tx_hash is not None
                failed = await manager.writer.confirm_prepared(prepared, submitted.tx_hash)
                assert failed.state == ChainOperationState.FAILED
                receipt = await rpc(
                    env["rpc_url"], "eth_getTransactionReceipt", [submitted.tx_hash]
                )
                assert receipt["status"] == "0x0"
            await verify(payment)
            assert bool(await events(payment) == before_events)
            attempts = await asyncio.gather(
                bank.post(use, json={"request_id": "req_race_issuer"}),
                recipient.post(use, json={"request_id": "req_race_recipient"}),
            )
            assert sorted(response.status_code for response in attempts) == [200, 409]
            winner_index = 0 if attempts[0].status_code == 200 else 1
            winner = attempts[winner_index].json()
            assert winner["status"] == "CONFIRMED"
            winner_client = bank if winner_index == 0 else recipient
            retry = await winner_client.post(use, json={"request_id": winner["request_id"]})
            assert retry.json()["operation_id"] == winner["operation_id"]
            assert retry.json()["tx_hash"] == winner["tx_hash"]
            conflict = await winner_client.post(
                f"/v2/proofs/{histories['bank']['proof_id']}/consume",
                json={"request_id": winner["request_id"]},
            )
            assert (
                conflict.status_code == 409 and conflict.json()["detail"] == "REQUEST_ID_CONFLICT"
            )
            replay = await recipient.post(use, json={"request_id": "req_replay"})
            assert replay.status_code == 409 and replay.json()["detail"] == "REPLAY_DETECTED"
            await verify(payment, "CONSUMED", ["REPLAY_DETECTED"])
            consumed_topic = "0x" + digest("ProofConsumed(bytes32,uint8,uint64)").hex()
            assert sum(log["topics"][0] == consumed_topic for log in await events(payment)) == 1
            path = f"/v2/issuer/proofs/{payment['proof_id']}/revoke"
            assert (
                await bank.post(path, json={"request_id": "req_revoke", "reason": "synthetic"})
            ).json()["status"] == "CONFIRMED"
            logs = await events(payment)
            repeated = await bank.post(
                path, json={"request_id": "req_revoke_again", "reason": "synthetic"}
            )
            assert (
                repeated.json()["chain_evidence"]["no_change"]
                and repeated.json()["tx_hash"] is None
            )
            assert bool(await events(payment) == logs)
            await verify(payment, "PROOF_REVOKED", ["PROOF_REVOKED", "REPLAY_DETECTED"])
            payment_state = await manager.reader(accounts["bank"].issuer_id).get_proof_state(
                payment["proof_id"], clock[0]
            )
            assert payment_state.revoked_at is not None and payment_state.consumed_at is not None
            revoke_topic = "0x" + digest("ProofRevoked(bytes32,uint64)").hex()
            assert sum(log["topics"][0] == revoke_topic for log in logs) == 1
            document_revoke = await office.post(
                f"/v2/issuer/proofs/{document['proof_id']}/revoke",
                json={"request_id": "req_revoke_document", "reason": "synthetic"},
            )
            assert document_revoke.json()["status"] == "CONFIRMED"
            await verify(document, "PROOF_REVOKED", ["PROOF_REVOKED"])
            same = await issue("bank", "same_request")
            same_path = f"/v2/proofs/{same['proof_id']}/consume"
            same_attempts = await asyncio.gather(
                *[recipient.post(same_path, json={"request_id": "req_same_use"}) for _ in range(2)]
            )
            assert all(response.status_code == 200 for response in same_attempts)
            assert len({response.json()["operation_id"] for response in same_attempts}) == 1
            assert len({response.json()["tx_hash"] for response in same_attempts}) == 1
            assert sum(log["topics"][0] == consumed_topic for log in await events(same)) == 1

            for role in ("bank", "office"):
                rotated = await clients[role].post(
                    "/v1/issuer/keys/rotate",
                    json=key_input
                    | {
                        "request_id": f"req_rotate_{role}",
                        "valid_until": (origin + timedelta(days=1)).isoformat(),
                    },
                )
                assert rotated.json()["status"] == "CONFIRMED"
                fresh = await issue(role, "rotated")
                assert fresh["key_id"] != histories[role]["key_id"]
                assert fresh["key_id"] == rotated.json()["target_id"]
                await verify(histories[role])
                selected = (await clients[role].get("/v1/issuer/keys")).json()
                assert [key["key_id"] for key in selected if key["selected"]] == [fresh["key_id"]]
            issuer_path = f"/v1/operator/issuers/{accounts['office'].issuer_id}"
            suspended = await admin.post(
                f"{issuer_path}/suspend", json={"request_id": "req_suspend", "reason": "synthetic"}
            )
            assert suspended.json()["status"] == "CONFIRMED"
            await verify(histories["office"], "ISSUER_SUSPENDED", ["ISSUER_SUSPENDED"])
            restored = await admin.post(
                f"{issuer_path}/reactivate",
                json={"request_id": "req_restore", "reason": "synthetic"},
            )
            assert restored.json()["status"] == "CONFIRMED"
            await verify(histories["office"])
            expires = {
                role: await issue(role, "expiry", lifetime=300) for role in ("bank", "office")
            }

            # Stop only the Anvil created by this fixture; W4 must hold current validity.
            async with database.session_factory() as db:
                outage_counts = [
                    await db.scalar(select(func.count()).select_from(model))
                    for model in (OperationRow, AuditEventRow)
                ]
            command(["docker", "stop", env["anvil"]])
            try:
                held = await public.post(
                    f"/v2/proofs/{expires['bank']['proof_id']}/verify",
                    json={"request_id": "req_rpc_unavailable"},
                )
                assert held.status_code == 200
                assert held.json()["verification_status"] == "INCONCLUSIVE"
                assert held.json()["lifecycle_status"] is None
                assert held.json()["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
                assert held.json()["checks"]["proof_status"] != "PASS"
                denied = await recipient.post(
                    f"/v2/proofs/{expires['bank']['proof_id']}/consume",
                    json={"request_id": "req_rpc_consume"},
                )
                assert denied.status_code == 503
                async with database.session_factory() as db:
                    assert bool(
                        outage_counts
                        == [
                            await db.scalar(select(func.count()).select_from(model))
                            for model in (OperationRow, AuditEventRow)
                        ]
                    )
            finally:
                command(["docker", "start", env["anvil"]])
            for _ in range(40):
                try:
                    await rpc(env["rpc_url"], "eth_chainId", [])
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(0.25)
            else:
                raise RuntimeError("Owned QA Anvil did not restart")
            await verify(expires["bank"])

            async def move_clock(moment):
                await rpc(env["rpc_url"], "evm_setNextBlockTimestamp", [int(moment.timestamp())])
                await rpc(env["rpc_url"], "evm_mine", [])
                clock[0] = moment
                header = await rpc(env["rpc_url"], "eth_getBlockByNumber", ["latest", False])
                assert int(header["timestamp"], 16) == int(moment.timestamp())

            await move_clock(origin + timedelta(seconds=121))
            # Old key periods ended, but issuance-time valid historical signatures remain valid.
            for proof in histories.values():
                await verify(proof)
            revoked_key = await bank.post(
                f"/v1/issuer/keys/{histories['bank']['key_id']}/revoke",
                json={"request_id": "req_compromise", "reason": "synthetic compromise"},
            )
            assert revoked_key.json()["status"] == "CONFIRMED"
            await verify(histories["bank"], "ISSUER_KEY_REVOKED", ["ISSUER_KEY_REVOKED"])
            revoked_office = await office.post(
                f"/v1/issuer/keys/{histories['office']['key_id']}/revoke",
                json={"request_id": "req_compromise_office", "reason": "synthetic compromise"},
            )
            assert revoked_office.json()["status"] == "CONFIRMED"
            await verify(histories["office"], "ISSUER_KEY_REVOKED", ["ISSUER_KEY_REVOKED"])
            assert (
                await recipient.post(
                    f"/v2/proofs/{histories['bank']['proof_id']}/consume",
                    json={"request_id": "req_compromised_use"},
                )
            ).status_code == 409
            for offset in (-1, 0, 1):
                await move_clock(origin + timedelta(seconds=300 + offset))
                for role, proof in expires.items():
                    await verify(
                        proof,
                        "ACTIVE" if offset < 0 else "EXPIRED",
                        [] if offset < 0 else ["PROOF_EXPIRED"],
                    )
                    if offset >= 0:
                        response = await recipient.post(
                            f"/v2/proofs/{proof['proof_id']}/consume",
                            json={"request_id": f"req_expired_{role}_{offset}"},
                        )
                        assert (
                            response.status_code == 409
                            and response.json()["detail"] == "PROOF_NOT_ACTIVE"
                        )
            # Read-only public/verify requests did not produce consumption events for these proofs.
            for proof in expires.values():
                assert not any(log["topics"][0] == consumed_topic for log in await events(proof))
    finally:
        await database.dispose()
