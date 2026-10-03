"""Prepare a new disposable W3 QA stack; never reads a personal .env.

Run from the repository root with its locked Python environment. Containers use
tmpfs/new container state and fixed loopback ports; existing resources fail closed.
Credentials and signer files remain in ignored build/w3-qa with private modes.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import shlex
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from originproof_api.accounts import password_hash
from originproof_api.chain_management import ChainManagement
from originproof_api.database import AccountRow, Database, IssuerApplicationRow
from originproof_api.settings import Settings
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/w3-qa"
FOUNDRY = (
    "ghcr.io/foundry-rs/foundry:v1.4.4@"
    "sha256:9584dfbb0e2e9bda80332b66a7cebed635fc9786638871df6b7594e39e678578"
)


def run(*args: str, env=None) -> str:
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
    if result.returncode:
        # Don't echo commands/env or SQL exceptions containing account material.
        raise RuntimeError(f"{args[0]} failed; exit {result.returncode}")
    return result.stdout.strip()


def private_file(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        stream.write(text)


async def initialize(env: dict[str, str]) -> None:
    db = Database(env["API_DATABASE_URL"])
    credentials = [
        {"username": role, "account_id": f"acct_{role}", "password": secrets.token_urlsafe(24)}
        for role in ("operator", "bank", "office", "recipient", "recipient_other", "recipient_new")
    ]
    try:
        async with db.session_factory() as session:
            session.add_all(
                [
                    AccountRow(
                        account_id=row["account_id"],
                        username=row["username"],
                        password_hash=password_hash(row["password"]),
                        role="issuer"
                        if row["username"] in ("bank", "office")
                        else ("operator" if row["username"] == "operator" else "recipient"),
                        issuer_id={
                            "bank": "iss_origin_mock_bank",
                            "office": "iss_origin_mock_office",
                        }.get(row["username"]),
                    )
                    for row in credentials
                ]
            )
            await session.commit()
    finally:
        await db.dispose()
    private_file(OUT / "accounts.json", json.dumps(credentials))


async def register(env: dict[str, str] | None = None) -> None:
    task_env = env or os.environ
    credentials = json.loads((OUT / "accounts.json").read_text())
    clients = {}
    try:
        for row in credentials[:3]:
            client = httpx.AsyncClient(base_url="http://127.0.0.1:14803", trust_env=False)
            clients[row["username"]] = client
            response = await client.post(
                "/v1/auth/login",
                json={
                    "username": row["username"],
                    "password": row["password"],
                },
            )
            assert response.status_code == 200, "synthetic login failed"
            client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        now = datetime.now(UTC).replace(microsecond=0)
        for name in ("bank", "office"):
            issuer, admin = clients[name], clients["operator"]
            if name == "bank":
                # Official MVP deployment already activates the bank. Verify that
                # actual chain state and seed its matching DB fixture; don't register twice.
                settings = Settings(
                    _env_file=None,
                    database_url=task_env["API_DATABASE_URL"],
                    blockchain_rpc_url=task_env["API_BLOCKCHAIN_RPC_URL"],
                    blockchain_manifest_path=task_env["API_BLOCKCHAIN_MANIFEST_PATH"],
                    signer_directory=task_env["API_SIGNER_DIRECTORY"],
                )
                database = Database(settings.database_url)
                try:
                    manager = ChainManagement(database, settings)
                    await manager.active_issuer("iss_origin_mock_bank")
                    async with database.session_factory() as session:
                        row = await session.scalar(
                            select(IssuerApplicationRow).where(
                                IssuerApplicationRow.issuer_id == "iss_origin_mock_bank"
                            )
                        )
                        if row is None:
                            row = IssuerApplicationRow(
                                application_id="app_d_seed_bank",
                                issuer_id="iss_origin_mock_bank",
                                applicant_account_id="acct_bank",
                                issuer_name="Origin Mock Bank",
                                status="ACTIVE",
                                decision_reason="official deployment seed",
                                decided_by_account_id="acct_operator",
                            )
                            session.add(row)
                        else:
                            row.status = "ACTIVE"
                        await session.commit()
                finally:
                    await database.dispose()
            else:
                response = await issuer.post(
                    "/v1/issuer-applications", json={"issuer_name": "Origin Mock Office"}
                )
                assert response.status_code == 201, "synthetic application failed"
                target = f"/v1/operator/issuer-applications/{response.json()['application_id']}"
                response = await admin.post(
                    target + "/decision", json={"decision": "APPROVE", "reason": "D synthetic QA"}
                )
                assert response.status_code == 200, "synthetic approval failed"
                response = await admin.post(
                    target + "/activate",
                    json={"request_id": f"req_d_activate_{name}", "reason": "D synthetic QA"},
                )
                assert response.status_code == 200 and response.json()["status"] == "CONFIRMED", (
                    "activation not confirmed"
                )
            response = await issuer.post(
                "/v1/issuer/keys",
                json={
                    "request_id": f"req_d_key_{name}",
                    "reason": "D synthetic QA",
                    "valid_from": (now - timedelta(minutes=1)).isoformat(),
                    "valid_until": (now + timedelta(days=7)).isoformat(),
                },
            )
            assert response.status_code == 200 and response.json()["status"] == "CONFIRMED", (
                "key not confirmed"
            )
    finally:
        for client in clients.values():
            await client.aclose()


def main() -> None:
    assert ROOT.is_relative_to(Path("/private/tmp")), "use a new disposable QA checkout"
    for path in (
        ROOT / "build/seed_manifest.json",
        ROOT / "build/mock_issuer_private_key.hex",
        ROOT / "packages/contracts/deployments/31337.local.json",
    ):
        if path.exists():
            raise SystemExit("existing generated seed/deployment found; use a fresh QA checkout")
    dotenv = ROOT / ".env"
    if dotenv.exists() and dotenv.read_text() != "LLM_PROVIDER=mock\nOPENAI_MODEL=gpt-6-luna\n":
        raise SystemExit("existing dotenv settings found; use a fresh QA checkout")
    if OUT.exists():
        raise SystemExit("build/w3-qa already exists; preserve it and use a fresh QA checkout")
    for port in (15433, 18543, 14803):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    OUT.mkdir(mode=0o700, parents=True)
    tag = secrets.token_hex(4)
    network = f"originproof-w3-d-qa-{tag}"
    pg, anvil = network + "-postgres", network + "-anvil"
    private_file(
        OUT / "resources.json", json.dumps({"network": network, "postgres": pg, "anvil": anvil})
    )
    password = secrets.token_urlsafe(24)
    private_file(
        OUT / "postgres.env",
        f"POSTGRES_USER=originproof\nPOSTGRES_DB=originproof_w3_d_qa\nPOSTGRES_PASSWORD={password}\n",
    )
    database_url = (
        f"postgresql+asyncpg://originproof:{password}@127.0.0.1:15433/originproof_w3_d_qa"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("API_", "OPENAI_", "LLM_"))
    }
    qa_env = {
        "API_DATABASE_URL": database_url,
        "SEED_DATABASE_URL": database_url,
        "API_BLOCKCHAIN_RPC_URL": "http://127.0.0.1:18543",
        "API_BLOCKCHAIN_MANIFEST_PATH": str(
            ROOT / "packages/contracts/deployments/31337.local.json"
        ),
        "API_SIGNER_DIRECTORY": str(OUT / "signers"),
        "API_FINALS_PAYMENT_ISSUER_ID": "iss_origin_mock_bank",
        "API_FINALS_DOCUMENT_ISSUER_ID": "iss_origin_mock_office",
        "LLM_PROVIDER": "mock",
        "OPENAI_MODEL": "gpt-6-luna",
        "PYTHONPATH": "apps/api/src:packages/python:services/analyzer/src",
        "TEST_DATABASE_URL": database_url,
        "TEST_CHAIN_RPC_URL": "http://127.0.0.1:18543",
        "TEST_CHAIN_MANIFEST": str(ROOT / "packages/contracts/deployments/31337.local.json"),
        "W3_LIVE_QA": "1",
        "W3_QA_DISPOSABLE": "1",
        "W3_QA_API_URL": "http://127.0.0.1:14803",
        "W3_QA_SIGNER_DIRECTORY": str(OUT / "signers"),
        "W3_QA_RPC_CONTAINER": anvil,
        "ORIGINPROOF_TEST_ACCOUNTS": str(OUT / "accounts.json"),
        "ORIGINPROOF_API_ORIGIN": "http://127.0.0.1:14803",
        "W3_WEB_URL": "http://127.0.0.1:3000",
    }
    env.update(qa_env)
    private_file(
        OUT / "runtime.env",
        "\n".join(
            f"export {key}={shlex.quote(value)}"
            for key, value in qa_env.items()
            if key.startswith(("API_", "TEST_", "W3_", "ORIGINPROOF_"))
            or key in ("PYTHONPATH", "LLM_PROVIDER", "OPENAI_MODEL")
        )
        + "\nunset OPENAI_API_KEY\n",
    )
    run("docker", "network", "create", network)
    run(
        "docker",
        "run",
        "--detach",
        "--name",
        pg,
        "--network",
        network,
        "--env-file",
        str(OUT / "postgres.env"),
        "--tmpfs",
        "/var/lib/postgresql/data",
        "-p",
        "127.0.0.1:15433:5432",
        "postgres:16.4-alpine",
    )
    run(
        "docker",
        "run",
        "--detach",
        "--name",
        anvil,
        "--network",
        network,
        "--network-alias",
        "anvil",
        "-p",
        "127.0.0.1:18543:8545",
        "--entrypoint",
        "anvil",
        FOUNDRY,
        "--host",
        "0.0.0.0",
        "--chain-id",
        "31337",
        "--state",
        "/tmp/w3-state.json",
        "--preserve-historical-states",
    )
    for _ in range(30):
        result = subprocess.run(
            ["docker", "exec", pg, "pg_isready", "-U", "originproof"], capture_output=True
        )
        if result.returncode == 0:
            break
        time.sleep(0.2)
    run(sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head", env=env)
    run(sys.executable, "scripts/fixtures/seed.py", env=env)
    signer = json.loads((ROOT / "build/seed_manifest.json").read_text())["signer"]
    sha = run("git", "rev-parse", "HEAD")
    run(
        "docker",
        "run",
        "--rm",
        "-e",
        "PYTHONPATH=apps/api/src:packages/python",
        "--network",
        network,
        "-v",
        f"{ROOT}/packages/contracts/deployments:/workspace/packages/contracts/deployments",
        "originproof-w3-d-qa-deployer",
        "uv",
        "run",
        "--package",
        "originproof-api",
        "python",
        "packages/contracts/script/deploy_local.py",
        "--rpc-url",
        "http://anvil:8545",
        "--signer",
        signer,
        "--source-commit-sha",
        sha,
    )
    asyncio.run(initialize(env))
    with (OUT / "api.log").open("x") as log:
        os.chmod(OUT / "api.log", 0o600)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "originproof_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "14803",
                "--no-access-log",
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    private_file(OUT / "api.pid", str(process.pid))
    with httpx.Client(trust_env=False) as client:
        for _ in range(30):
            try:
                if client.get("http://127.0.0.1:14803/health/ready").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("isolated API did not become ready")
    asyncio.run(register(env))
    print(
        "Prepared new isolated W3 PostgreSQL/Anvil/API, two approved issuers and synthetic accounts"
    )
    print("Private runtime settings: build/w3-qa/runtime.env")


if __name__ == "__main__":
    main()
