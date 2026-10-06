"""D's opt-in failure QA: real API processes, disposable PostgreSQL and Anvil.

Build infra/docker/deployer.Dockerfile as originproof-w2-recovery-deployer,
then run with W2_RECOVERY_QA=1. No existing .env, database or service is used.
"""

import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, AuditEventRow, Database, OperationRow
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[2]
FOUNDRY = (
    "ghcr.io/foundry-rs/foundry:v1.4.4@"
    "sha256:9584dfbb0e2e9bda80332b66a7cebed635fc9786638871df6b7594e39e678578"
)
pytestmark = pytest.mark.skipif(
    os.getenv("W2_RECOVERY_QA") != "1", reason="disposable process QA opt-in"
)


def command(*args, env=None):
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=120)
    if result.returncode:
        # Do not include environment, API payloads, credentials or deployment logs.
        raise RuntimeError(f"{args[0]} failed with exit code {result.returncode}")
    return result.stdout.decode().strip()


def wait_ready(check):
    for _ in range(150):
        try:
            if check():
                return
        except (httpx.HTTPError, RuntimeError):
            pass
        time.sleep(0.1)
    raise RuntimeError("disposable service did not become ready")


class Relay:
    """Loopback fault injection; forwards actual requests, records only RPC names."""

    def __init__(self, upstream):
        self.upstream = upstream
        self.mode = None
        self.methods = []
        relay = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                method = json.loads(body).get("method")
                relay.methods.append(method)
                if relay.mode == "offline":
                    self.close_connection = True
                    return
                if relay.mode == "receipt_timeout" and method == "eth_getTransactionReceipt":
                    threading.Event().wait(6)
                    self.close_connection = True
                    return
                headers = {
                    key: value
                    for key, value in self.headers.items()
                    if key.lower() not in ("host", "content-length", "connection")
                }
                with httpx.Client(timeout=10, trust_env=False) as client:
                    response = client.post(
                        relay.upstream + self.path, content=body, headers=headers
                    )
                if relay.mode == "drop_api" or (
                    relay.mode == "drop_send" and method == "eth_sendTransaction"
                ):
                    relay.mode = None
                    self.close_connection = True
                    return
                self.send_response(response.status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response.content)))
                self.end_headers()
                self.wfile.write(response.content)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class ApiProcess:
    def __init__(self, env):
        self.env = env
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.process = None

    def start(self):
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "originproof_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--no-access-log",
            ],
            cwd=ROOT,
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with httpx.Client(timeout=1, trust_env=False) as client:
            wait_ready(lambda: client.get(self.url + "/health/ready").status_code == 200)

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def restart(self):
        old_pid = self.process.pid
        self.stop()
        self.start()
        assert self.process.pid != old_pid


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    directory = tmp_path_factory.mktemp("w2-recovery")
    prefix = "originproof-w2-qa-" + uuid4().hex[:12]
    containers = []
    relays = []
    api = None
    network_created = False
    try:
        command("docker", "network", "create", prefix)
        network_created = True
        db_name, anvil_name, deploy_name = (
            prefix + suffix for suffix in ("-db", "-anvil", "-deploy")
        )
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env["POSTGRES_PASSWORD"] = secrets.token_urlsafe(24)
        for name, args in (
            (
                db_name,
                [
                    "--tmpfs",
                    "/var/lib/postgresql/data",
                    "-p",
                    "127.0.0.1::5432",
                    "-e",
                    "POSTGRES_PASSWORD",
                    "-e",
                    "POSTGRES_DB=w2_qa",
                    "postgres:16-alpine",
                ],
            ),
            (
                anvil_name,
                [
                    "--network-alias",
                    "anvil",
                    "-p",
                    "127.0.0.1::8545",
                    "--entrypoint",
                    "anvil",
                    FOUNDRY,
                    "--host",
                    "0.0.0.0",
                    "--silent",
                    "--chain-id",
                    "31337",
                    "--state",
                    "/tmp/w2-state.json",
                    "--preserve-historical-states",
                ],
            ),
        ):
            command("docker", "create", "--name", name, "--network", prefix, *args, env=env)
            containers.append(name)
            command("docker", "start", name)
        port = command("docker", "port", db_name, "5432/tcp").split(":")[-1]
        db_url = f"postgresql+asyncpg://postgres:{env['POSTGRES_PASSWORD']}@127.0.0.1:{port}/w2_qa"
        wait_ready(lambda: command("docker", "exec", db_name, "pg_isready", "-U", "postgres") != "")
        rpc_port = command("docker", "port", anvil_name, "8545/tcp").split(":")[-1]
        rpc_url = "http://127.0.0.1:" + rpc_port
        with httpx.Client(timeout=1, trust_env=False) as client:
            wait_ready(
                lambda: client.post(
                    rpc_url, json={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}
                )
                .json()
                .get("result")
                == "0x7a69"
            )
        sha = command("git", "rev-parse", "HEAD")
        command(
            "docker",
            "create",
            "--name",
            deploy_name,
            "--network",
            prefix,
            "originproof-w2-recovery-deployer",
            "uv",
            "run",
            "--package",
            "originproof-api",
            "python",
            "packages/contracts/script/deploy_local.py",
            "--rpc-url",
            "http://anvil:8545",
            "--signer",
            "0x" + "33" * 20,
            "--source-commit-sha",
            sha,
        )
        containers.append(deploy_name)
        command("docker", "start", "-a", deploy_name)
        assert command("docker", "inspect", "--format", "{{.State.ExitCode}}", deploy_name) == "0"
        manifest = directory / "manifest.json"
        command(
            "docker",
            "cp",
            deploy_name + ":/workspace/packages/contracts/deployments/31337.local.json",
            str(manifest),
        )
        assert json.loads(manifest.read_text())["source_commit_sha"] == sha
        rpc_relay = Relay(rpc_url)
        relays.append(rpc_relay)
        env.update(
            API_DATABASE_URL=db_url,
            API_BLOCKCHAIN_RPC_URL=rpc_relay.url,
            API_BLOCKCHAIN_MANIFEST_PATH=str(manifest),
            API_SIGNER_DIRECTORY=str(directory / "signers"),
            API_SESSION_COOKIE_SECURE="false",
            LLM_PROVIDER="mock",
            OPENAI_MODEL="gpt-6-luna",
        )
        command(
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "apps/api/alembic.ini",
            "upgrade",
            "head",
            env=env,
        )
        api = ApiProcess(env)
        api.start()
        api_relay = Relay(api.url)
        relays.append(api_relay)
        yield {
            "db_url": db_url,
            "rpc_url": rpc_url,
            "rpc": rpc_relay,
            "api": api,
            "http": api_relay,
            "anvil": anvil_name,
            "manifest": manifest,
            "network": prefix,
        }
    finally:
        if api is not None:
            api.stop()
        for relay in reversed(relays):
            relay.close()
        for name in reversed(containers):
            command("docker", "rm", "-f", name)
        if network_created:
            command("docker", "network", "rm", prefix)


async def test_live_failure_recovery_and_process_restart(stack):
    """Nine boundaries; a single test keeps process/state changes ordered."""
    database = Database(stack["db_url"])
    password = secrets.token_urlsafe(24)
    suffix = uuid4().hex[:12]
    accounts = [
        AccountRow(
            account_id=f"acct_{role}_{suffix}",
            username=f"{role}_{suffix}",
            password_hash=password_hash(password),
            role="operator" if role == "operator" else "issuer",
            issuer_id=None if role == "operator" else f"iss_{role}_{suffix}",
        )
        for role in ("operator", "approved", "rejected")
    ]
    try:
        async with database.session_factory() as db:
            db.add_all(accounts)
            await db.commit()
        async with (
            httpx.AsyncClient(base_url=stack["api"].url, timeout=20, trust_env=False) as admin,
            httpx.AsyncClient(base_url=stack["api"].url, timeout=20, trust_env=False) as issuer,
            httpx.AsyncClient(base_url=stack["api"].url, timeout=20, trust_env=False) as rejected,
        ):
            for client, account in zip((admin, issuer, rejected), accounts, strict=True):
                response = await client.post(
                    "/v1/auth/login", json={"username": account.username, "password": password}
                )
                assert response.status_code == 200
                client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
            now = datetime.now(UTC).replace(microsecond=0)
            key_body = {
                "request_id": "req_key_" + suffix,
                "reason": "synthetic QA",
                "valid_from": now.isoformat(),
                "valid_until": (now + timedelta(days=1)).isoformat(),
            }
            applications = []
            for client in (issuer, rejected):
                response = await client.post(
                    "/v1/issuer-applications", json={"issuer_name": "Synthetic QA"}
                )
                assert response.status_code == 201 and response.json()["status"] == "PENDING_REVIEW"
                applications.append(response.json()["application_id"])
                denied = await client.post("/v1/issuer/keys", json=key_body)
                assert denied.status_code == 409 and denied.json()["detail"] == "ISSUER_NOT_ACTIVE"
            for application_id, decision in zip(applications, ("APPROVE", "REJECT"), strict=True):
                response = await admin.post(
                    f"/v1/operator/issuer-applications/{application_id}/decision",
                    json={"decision": decision, "reason": "synthetic QA"},
                )
                assert response.status_code == 200
            assert (await rejected.post("/v1/issuer/keys", json=key_body)).status_code == 409
            assert (await issuer.post("/v1/issuer/keys", json=key_body)).status_code == 409
            async with database.session_factory() as db:
                assert await db.scalar(select(func.count()).select_from(OperationRow)) == 0
                assert await db.scalar(select(func.count()).select_from(AuditEventRow)) == 2
            assert "eth_sendTransaction" not in stack["rpc"].methods
            path = f"/v1/operator/issuer-applications/{applications[0]}/activate"
            body = {"request_id": "req_activate_" + suffix, "reason": "synthetic QA"}
            assert (await issuer.post(path, json=body)).status_code == 403
            assert (await admin.post(path, json=body | {"role": "operator"})).status_code == 422
            stack["rpc"].mode = "offline"
            assert (await admin.post(path, json=body)).status_code == 503
            assert "eth_sendTransaction" not in stack["rpc"].methods
            # Real Anvil submission succeeds, but the RPC response/hash is dropped.
            stack["rpc"].mode = "drop_send"
            uncertain = await admin.post(path, json=body)
            assert uncertain.status_code == 200 and uncertain.json()["status"] == "UNKNOWN"
            operation_id = uncertain.json()["operation_id"]
            async with database.session_factory() as db:
                stored = await db.get(OperationRow, operation_id)
                assert stored.tx_hash is None and stored.recovery_reference["nonce"] is not None
            assert stack["rpc"].methods.count("eth_sendTransaction") == 1
            assert (
                await issuer.post(
                    "/v1/issuer/keys", json=key_body | {"issuer_id": accounts[2].issuer_id}
                )
            ).status_code == 422
            await asyncio.to_thread(stack["api"].restart)
            recovered = await admin.post(f"/v1/operations/{operation_id}/recover")
            assert recovered.status_code == 200 and recovered.json()["status"] == "CONFIRMED"
            assert recovered.json()["chain_evidence"]["confirmation_count"] >= 1
            assert stack["rpc"].methods.count("eth_sendTransaction") == 1
            # Actual receipt request exceeds the adapter's five-second timeout.
            stack["rpc"].mode = "receipt_timeout"
            started = time.monotonic()
            key = await issuer.post("/v1/issuer/keys", json=key_body)
            assert time.monotonic() - started >= 5
            assert key.status_code == 200 and key.json()["status"] == "UNKNOWN"
            assert key.json()["tx_hash"] and key.json()["error_code"] == "DEPENDENCY_UNAVAILABLE"
            sends = stack["rpc"].methods.count("eth_sendTransaction")
            stack["rpc"].mode = None
            await asyncio.to_thread(stack["api"].restart)
            response = await issuer.post(f"/v1/operations/{key.json()['operation_id']}/recover")
            assert response.status_code == 200 and response.json()["status"] == "CONFIRMED"
            assert response.json()["chain_evidence"]["reread_block_number"] is not None
            assert stack["rpc"].methods.count("eth_sendTransaction") == sends
            keys = (await issuer.get("/v1/issuer/keys")).json()
            assert len(keys) == 1 and keys[0]["status"] == "ACTIVE" and keys[0]["selected"]
            assert not {"secret_ref", "private_key", "password", "token"}.intersection(keys[0])
            key_id = keys[0]["key_id"]
            assert (await rejected.get(f"/v1/issuer/keys/{key_id}")).status_code == 404
            # SIGTERM/restart dumps and reloads this container's own chain state.
            await asyncio.to_thread(command, "docker", "restart", "--timeout", "10", stack["anvil"])
            # Docker may allocate a different published port on restart.
            port = await asyncio.to_thread(command, "docker", "port", stack["anvil"], "8545/tcp")
            stack["rpc_url"] = "http://127.0.0.1:" + port.split(":")[-1]
            stack["rpc"].upstream = stack["rpc_url"]
            async with httpx.AsyncClient(timeout=1, trust_env=False) as rpc:
                for _ in range(100):
                    try:
                        if (
                            await rpc.post(
                                stack["rpc_url"],
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "eth_chainId",
                                    "params": [],
                                },
                            )
                        ).json().get("result") == "0x7a69":
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("restarted disposable Anvil unavailable")
            await asyncio.to_thread(stack["api"].restart)
            assert (await issuer.get("/v1/issuer/status")).json()["status"] == "ACTIVE"
            after_restart = (await issuer.get(f"/v1/issuer/keys/{key_id}")).json()
            assert after_restart["status"] == "ACTIVE" and after_restart["selected"]
            assert after_restart["signer"] == keys[0]["signer"]
            assert after_restart["deployment_id"] == keys[0]["deployment_id"]
            async with httpx.AsyncClient(
                base_url=stack["api"].url, timeout=10, trust_env=False
            ) as fresh_session:
                login = await fresh_session.post(
                    "/v1/auth/login",
                    json={"username": accounts[1].username, "password": password},
                )
                assert login.status_code == 200
                fresh_keys = await fresh_session.get("/v1/issuer/keys")
                assert fresh_keys.status_code == 200
                assert fresh_keys.json() == [after_restart]
            # Successful server response is lost only at the HTTP client boundary.
            revoke_body = {"request_id": "req_revoke_" + suffix, "reason": "synthetic QA"}
            revoke_path = f"/v1/issuer/keys/{key_id}/revoke"
            stack["http"].mode = "drop_api"
            with pytest.raises(httpx.RemoteProtocolError):
                await issuer.post(stack["http"].url + revoke_path, json=revoke_body)
            sends = stack["rpc"].methods.count("eth_sendTransaction")
            retry = await issuer.post(revoke_path, json=revoke_body)
            assert retry.status_code == 200 and retry.json()["status"] == "CONFIRMED"
            assert stack["rpc"].methods.count("eth_sendTransaction") == sends
            async with database.session_factory() as db:
                rows = list(
                    await db.scalars(
                        select(OperationRow).where(
                            OperationRow.request_id == revoke_body["request_id"]
                        )
                    )
                )
                assert len(rows) == 1 and rows[0].operation_id == retry.json()["operation_id"]
                assert rows[0].tx_hash == retry.json()["tx_hash"]
            assert (await issuer.get(f"/v1/issuer/keys/{key_id}")).json()["status"] == "REVOKED"
    finally:
        await database.dispose()


def test_existing_postgres_and_chain_acceptance(stack):
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.update(
        TEST_DATABASE_URL=stack["db_url"],
        TEST_CHAIN_RPC_URL=stack["rpc_url"],
        TEST_CHAIN_MANIFEST=str(stack["manifest"]),
        LLM_PROVIDER="mock",
        OPENAI_MODEL="gpt-6-luna",
    )
    result = command(
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "apps/api/tests/test_live_w1_w2.py",
        "apps/api/tests/test_live_w2_chain.py",
        "--tb=short",
        env=env,
    )
    assert "3 passed" in result


def test_existing_indexer_local_chain_acceptance(stack):
    # The existing opt-in deploy helper uses forge inside the standard container.
    # All ABI/manifest outputs remain in this disposable container filesystem.
    result = command(
        "docker",
        "run",
        "--rm",
        "--network",
        stack["network"],
        "--mount",
        f"type=bind,source={ROOT / 'services/indexer'},target=/workspace/services/indexer,readonly",
        "-e",
        "M4_LIVE_TEST=1",
        "-e",
        "M4_RPC_URL=http://anvil:8545",
        "-e",
        "M4_SOURCE_COMMIT_SHA=" + command("git", "rev-parse", "HEAD"),
        "-e",
        "LLM_PROVIDER=mock",
        "-e",
        "OPENAI_MODEL=gpt-6-luna",
        "-e",
        "PYTHONPATH=apps/api/src:packages/python:services/indexer/src:packages/contracts/script",
        "originproof-w2-recovery-deployer",
        "uv",
        "run",
        "--package",
        "originproof-api",
        "--with",
        "pytest==8.4.2",
        "--with",
        "pytest-asyncio==0.25.3",
        "pytest",
        "-q",
        "services/indexer/tests/test_live_chain.py",
        "--tb=short",
    )
    assert "1 passed" in result
