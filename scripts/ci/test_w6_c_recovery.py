"""Opt-in C integration: disposable PostgreSQL, actual Anvil and separate API processes.

W6_C_LIVE_TEST=1 make test-w6-c-live
No existing Compose project or volume is modified. Host forge/anvil and Docker are required.
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from originproof_api.database import Database, FinalsProofRow, OperationRow
from originproof_api.signers import verify_signer
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.getenv("W6_C_LIVE_TEST") != "1", reason="disposable C live opt-in"
)


def command(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def wait_http(url, predicate=lambda response: response.status_code == 200):
    async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
        for _ in range(100):
            try:
                if predicate(await client.get(url)):
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise AssertionError("local API did not reach expected readiness")


class LiveState(SimpleNamespace):
    def __repr__(self):
        return "<disposable C live environment; credentials omitted>"


@pytest.fixture
async def live(tmp_path, monkeypatch):
    assert shutil.which("forge") and shutil.which("anvil"), "fixed Foundry binaries required"
    name = "originproof-c-validation-" + uuid4().hex[:12]
    rpc_port, api_port, pg_port = port(), port(), port()
    rpc_url, api_url = f"http://127.0.0.1:{rpc_port}", f"http://127.0.0.1:{api_port}"
    postgres = None
    anvil = None
    api = None
    server = None
    database_url = f"postgresql+asyncpg://originproof:originproof@127.0.0.1:{pg_port}/originproof"
    env = os.environ | {
        "PYTHONPATH": str(ROOT / "apps/api/src")
        + ":"
        + str(ROOT / "packages/python")
        + ":"
        + str(ROOT / "services/indexer/src"),
        "API_DATABASE_URL": database_url,
        "API_SIGNER_DIRECTORY": str(tmp_path / "signers"),
        "API_FINALS_PAYMENT_ISSUER_ID": "iss_c_bank_" + name[-12:],
        "API_FINALS_DOCUMENT_ISSUER_ID": "iss_c_office_" + name[-12:],
        "API_PROJECTION_ENABLED": "true",
        "API_PROJECTION_POLL_SECONDS": "1",
        "API_REQUESTS_PER_MINUTE": "1000",
        "API_LOGINS_PER_MINUTE": "100",
    }
    flags = SimpleNamespace(
        drop_submission=False,
        hold_receipt=False,
        offline=False,
        reached=threading.Event(),
        release=threading.Event(),
    )
    try:
        command(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "originproof.validation=true",
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-p",
            f"127.0.0.1:{pg_port}:5432",
            "-e",
            "POSTGRES_USER=originproof",
            "-e",
            "POSTGRES_PASSWORD=originproof",
            "-e",
            "POSTGRES_DB=originproof",
            "postgres:16.4-alpine",
        )
        postgres = name
        for _ in range(100):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "originproof"], capture_output=True
            )
            if ready.returncode == 0:
                break
            await asyncio.sleep(0.1)
        else:
            raise AssertionError("disposable PostgreSQL did not start")
        anvil = subprocess.Popen(
            ["anvil", "--port", str(rpc_port), "--chain-id", "31337", "--silent"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        async with httpx.AsyncClient(timeout=2, trust_env=False) as rpc_client:
            for _ in range(100):
                try:
                    result = await rpc_client.post(
                        rpc_url,
                        json={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []},
                    )
                    if result.json().get("result") == "0x7a69":
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("Anvil did not start")
        sys.path.insert(0, str(ROOT / "packages/contracts/script"))
        from deploy_local import deploy
        from eth_keys import keys

        manifest = await asyncio.to_thread(
            deploy,
            rpc_url,
            keys.PrivateKey(os.urandom(32)).public_key.to_checksum_address(),
            command("git", "rev-parse", "HEAD", text=True).strip(),
        )

        # Test-local JSON-RPC relay models actual forwarding followed by response loss.
        class Relay(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if flags.offline:
                    response = {"jsonrpc": "2.0", "id": body["id"], "error": {"code": -32000}}
                else:
                    with httpx.Client(timeout=10, trust_env=False) as client:
                        response = client.post(rpc_url, json=body).json()
                    if body["method"] == "eth_sendTransaction" and flags.drop_submission:
                        flags.drop_submission = False
                        response = {
                            "jsonrpc": "2.0",
                            "id": body["id"],
                            "error": {"code": -32000, "message": "already known"},
                        }
                    if body["method"] == "eth_getTransactionReceipt" and flags.hold_receipt:
                        flags.reached.set()
                        flags.release.wait(timeout=15)
                try:
                    encoded = json.dumps(response).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Relay)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        env["API_BLOCKCHAIN_RPC_URL"] = f"http://127.0.0.1:{server.server_port}"
        env["API_BLOCKCHAIN_MANIFEST_PATH"] = str(manifest)
        command(
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "apps/api/alembic.ini",
            "upgrade",
            "head",
            cwd=ROOT,
            env=env,
        )
        command(sys.executable, "scripts/fixtures/seed_accounts.py", "--p0", cwd=ROOT, env=env)

        def start():
            nonlocal api
            api = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "originproof_api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--no-proxy-headers",
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        def stop():
            nonlocal api
            if api is not None and api.poll() is None:
                api.kill()
                api.wait(timeout=10)
            api = None

        start()
        await wait_http(api_url + "/health/ready")
        credential = json.loads((tmp_path / "signers/test-accounts.json").read_text())["password"]
        clients = [
            httpx.AsyncClient(base_url=api_url, timeout=20, trust_env=False) for _ in range(5)
        ]
        for client, username in zip(
            clients, ("operator", "bank", "office", "recipient", "recipient_other"), strict=True
        ):
            login = await client.post(
                "/v1/auth/login", json={"username": username, "password": credential}
            )
            assert login.status_code == 200
            client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        admin, bank, office, recipient, other = clients
        now = datetime.now(UTC).replace(microsecond=0)
        for issuer, kind in ((bank, "bank"), (office, "office")):
            application = await issuer.post(
                "/v1/issuer-applications", json={"issuer_name": "Synthetic " + kind}
            )
            assert application.status_code == 201
            path = f"/v1/operator/issuer-applications/{application.json()['application_id']}"
            assert (
                await admin.post(
                    path + "/decision", json={"decision": "APPROVE", "reason": "synthetic"}
                )
            ).status_code == 200
            assert (
                await admin.post(
                    path + "/activate",
                    json={"request_id": "req_activate_" + kind, "reason": "synthetic"},
                )
            ).json()["status"] == "CONFIRMED"
            assert (
                await issuer.post(
                    "/v1/issuer/keys",
                    json={
                        "request_id": "req_key_" + kind,
                        "reason": "synthetic",
                        "valid_from": (now - timedelta(minutes=1)).isoformat(),
                        "valid_until": (now + timedelta(days=1)).isoformat(),
                    },
                )
            ).json()["status"] == "CONFIRMED"
        recipients = (await bank.get("/v2/issuer/recipients")).json()
        recipient_id = next(
            row["recipient_id"] for row in recipients if row["label"] == "recipient"
        )
        database = Database(database_url)
        state = LiveState(
            tmp=tmp_path,
            name=name,
            env=env,
            flags=flags,
            start=start,
            stop=stop,
            api_url=api_url,
            rpc_url=rpc_url,
            manifest=manifest,
            database=database,
            clients=clients,
            recipient_id=recipient_id,
        )
        yield state
        await database.dispose()
        for client in clients:
            await client.aclose()
    finally:
        flags.release.set()
        if api is not None and api.poll() is None:
            api.kill()
            api.wait(timeout=10)
        if server is not None:
            server.shutdown()
            server.server_close()
        if anvil is not None:
            anvil.terminate()
            anvil.wait(timeout=10)
        if postgres:
            command("docker", "rm", "-f", postgres)


def issue_body(live, request_id, kind="PAYMENT_REQUEST"):
    content = {
        "proof_type": kind,
        "amount_minor": 10000,
        "currency": "KRW",
        "target_ref": "synthetic",
    }
    if kind == "OFFICIAL_DOCUMENT":
        content = {
            "proof_type": kind,
            "institution_code": "ORIGIN_MOCK_OFFICE",
            "document_type": "Certificate",
            "document_number": "SYNTHETIC",
            "version": 1,
        }
    return {
        "request_id": request_id,
        "recipient_id": live.recipient_id,
        "expires_at": (datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)).isoformat(),
        "content": content,
    }


async def test_actual_process_restart_unknown_submission_and_consume(live):
    admin, bank, office, recipient, other = live.clients
    live.flags.drop_submission = True
    response = await bank.post("/v2/issuer/proofs", json=issue_body(live, "req_ambiguous"))
    assert response.status_code == 200
    proof = response.json()
    operation_id = proof["registration_operation_id"]
    assert proof["registration_status"] == "UNKNOWN"
    async with live.database.session_factory() as db:
        before = await db.get(OperationRow, operation_id)
        assert before.tx_hash is None and before.recovery_reference
        reference = before.recovery_reference.copy()
    assert (await office.get(f"/v1/operations/{operation_id}")).status_code == 404
    live.stop()
    live.start()
    await wait_http(live.api_url + "/health/ready")
    recovered = await bank.post(f"/v1/operations/{operation_id}/recover")
    assert recovered.json()["status"] == "CONFIRMED"
    original_tx = recovered.json()["tx_hash"]
    async with live.database.session_factory() as db:
        assert (await db.get(OperationRow, operation_id)).recovery_reference == reference
    # Unrelated successful tx must not confirm even when the expected chain state already matches.
    other_op = (
        await office.post(
            "/v2/issuer/proofs", json=issue_body(live, "req_document", "OFFICIAL_DOCUMENT")
        )
    ).json()["registration_operation_id"]
    async with live.database.session_factory() as db:
        unrelated = await db.get(OperationRow, other_op)
        row = await db.get(OperationRow, operation_id)
        row.status, row.tx_hash = "UNKNOWN", unrelated.tx_hash
        await db.commit()
    mismatched = await bank.post(f"/v1/operations/{operation_id}/recover")
    assert mismatched.json()["status"] == "UNKNOWN"
    assert mismatched.json()["error_code"] == "TRANSACTION_NOT_MATCHED"
    async with live.database.session_factory() as db:
        row = await db.get(OperationRow, operation_id)
        row.tx_hash = original_tx
        await db.commit()
    assert (await bank.post(f"/v1/operations/{operation_id}/recover")).json()[
        "status"
    ] == "CONFIRMED"
    # Kill the real API after consume transaction submission but before receipt processing.
    live.flags.hold_receipt = True
    path = f"/v2/proofs/{proof['proof_id']}/consume"
    task = asyncio.create_task(recipient.post(path, json={"request_id": "req_crash_consume"}))
    assert await asyncio.to_thread(live.flags.reached.wait, 10)
    live.stop()
    live.flags.hold_receipt = False
    live.flags.release.set()
    try:
        await task
        pytest.fail("killed API unexpectedly returned a response")
    except httpx.HTTPError:
        pass
    async with live.database.session_factory() as db:
        saved = await db.scalar(
            select(OperationRow).where(OperationRow.request_id == "req_crash_consume")
        )
        assert saved.status == "SUBMITTED" and saved.tx_hash and saved.recovery_reference
        saved_hash, saved_ref, saved_id = (
            saved.tx_hash,
            saved.recovery_reference.copy(),
            saved.operation_id,
        )
    live.start()
    await wait_http(live.api_url + "/health/ready")
    recovered = await recipient.post(f"/v1/operations/{saved_id}/recover")
    assert recovered.json()["status"] == "CONFIRMED" and recovered.json()["tx_hash"] == saved_hash
    async with live.database.session_factory() as db:
        assert (await db.get(OperationRow, saved_id)).recovery_reference == saved_ref
    assert (await recipient.post(path, json={"request_id": "req_crash_consume"})).json()[
        "operation_id"
    ] == saved_id
    assert (await other.post(path, json={"request_id": "req_wrong_recipient"})).status_code == 404
    assert (await recipient.post(path, json={"request_id": "req_second_use"})).status_code == 409
    verified = await recipient.post(
        f"/v2/proofs/{proof['proof_id']}/verify", json={"request_id": "req_verify"}
    )
    assert verified.json()["lifecycle_status"] == "CONSUMED"
    # Distinct concurrent issue requests share no duplicate reservation; same ID is immutable.
    body = issue_body(live, "req_parallel_issue")
    first, second = await asyncio.gather(
        bank.post("/v2/issuer/proofs", json=body), bank.post("/v2/issuer/proofs", json=body)
    )
    assert first.status_code == second.status_code == 200 and first.json() == second.json()
    use = f"/v2/proofs/{first.json()['proof_id']}/consume"
    first, second = await asyncio.gather(
        recipient.post(use, json={"request_id": "req_compete_1"}),
        recipient.post(use, json={"request_id": "req_compete_2"}),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    live.flags.offline = True
    try:
        held = await recipient.post(
            f"/v2/proofs/{proof['proof_id']}/verify", json={"request_id": "req_offline"}
        )
        assert held.json()["verification_status"] == "INCONCLUSIVE"
        assert held.json()["lifecycle_status"] is None
        await asyncio.sleep(1.5)
        assert (await admin.get("/v1/chain-sync")).json()["status"] == "RECOVERING"
        assert (await admin.get("/health/ready")).status_code == 503
    finally:
        live.flags.offline = False
    await wait_http(live.api_url + "/health/ready")


async def test_actual_backup_restore_migration_and_signer_preservation(live):
    _, bank, _, recipient, _ = live.clients
    original_body = issue_body(live, "req_backup")
    response = await bank.post("/v2/issuer/proofs", json=original_body)
    proof = response.json()
    live.stop()
    dump = command(
        "docker", "exec", live.name, "pg_dump", "-U", "originproof", "-Fc", "originproof"
    )
    backup = live.tmp / "database.dump"
    backup.touch(mode=0o600)
    backup.write_bytes(dump)
    assert backup.stat().st_mode & 0o777 == 0o600
    signers = live.tmp / "restored-signers"
    shutil.copytree(live.tmp / "signers", signers)
    command("docker", "exec", live.name, "createdb", "-U", "originproof", "originproof_restore")
    command(
        "docker",
        "exec",
        "-i",
        live.name,
        "pg_restore",
        "--exit-on-error",
        "--no-owner",
        "-U",
        "originproof",
        "-d",
        "originproof_restore",
        input=dump,
    )
    live.env["API_DATABASE_URL"] = (
        live.env["API_DATABASE_URL"].removesuffix("originproof") + "originproof_restore"
    )
    live.env["API_SIGNER_DIRECTORY"] = str(signers)
    # Fallback 0006 -> 0005 removes only projection; API data/key references stay.
    command(
        sys.executable,
        "-m",
        "alembic",
        "-c",
        "apps/api/alembic.ini",
        "downgrade",
        "20261001_0005",
        cwd=ROOT,
        env=live.env,
    )
    command(
        sys.executable,
        "-m",
        "alembic",
        "-c",
        "apps/api/alembic.ini",
        "upgrade",
        "head",
        cwd=ROOT,
        env=live.env,
    )
    # Re-running seed never replaces the preserved password or institution ownership.
    command(sys.executable, "scripts/fixtures/seed_accounts.py", "--p0", cwd=ROOT, env=live.env)
    restored = Database(live.env["API_DATABASE_URL"])
    try:
        async with restored.session_factory() as db:
            from originproof_api.database import IssuerKeyRow

            row = await db.get(FinalsProofRow, proof["proof_id"])
            key = await db.get(IssuerKeyRow, row.key_id)
            verify_signer(str(signers), key.secret_ref, key.signer)
        live.start()
        await wait_http(live.api_url + "/health/ready")
        result = await recipient.post(
            f"/v2/proofs/{proof['proof_id']}/verify", json={"request_id": "req_restored"}
        )
        assert result.json()["verification_status"] == "VERIFIED"
        assert result.json()["lifecycle_status"] == "ACTIVE"
        assert (await bank.post("/v2/issuer/proofs", json=original_body)).json()[
            "proof_id"
        ] == proof["proof_id"]
        # A restored DB and a fresh deployment sharing chain_id must remain separate.
        live.stop()
        old_manifest = json.loads(Path(live.manifest).read_text())
        sys.path.insert(0, str(ROOT / "packages/contracts/script"))
        from deploy_local import deploy
        from eth_keys import keys

        new_manifest = await asyncio.to_thread(
            deploy,
            live.rpc_url,
            keys.PrivateKey(os.urandom(32)).public_key.to_checksum_address(),
            command("git", "rev-parse", "HEAD", text=True).strip(),
        )
        assert (
            json.loads(new_manifest.read_text())["deployment_id"] != old_manifest["deployment_id"]
        )
        live.start()
        await wait_http(live.api_url + "/health/ready")
        result = await bank.post(f"/v1/operations/{proof['registration_operation_id']}/recover")
        assert result.status_code == 409 and result.json()["detail"] == "DEPLOYMENT_CHANGED"
        result = await recipient.post(
            f"/v2/proofs/{proof['proof_id']}/verify", json={"request_id": "req_new_deployment"}
        )
        assert result.json()["verification_status"] == "INCONCLUSIVE"
    finally:
        await restored.dispose()
