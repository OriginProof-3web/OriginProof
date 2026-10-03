"""D's actual W2 browser QA; owns only new disposable test resources.

Reuses PR #45's PostgreSQL/Anvil/API fixture. API seeding is solely test
preparation, never evidence that missing web actions have been implemented.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import secrets
import signal
import socket
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, Database, IssuerApplicationRow, OperationRow
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/w2-browser-qa"


def private_file(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        stream.write(value)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def recovery_module():
    spec = importlib.util.spec_from_file_location(
        "w2_recovery", ROOT / "scripts/ci/test_w2_recovery_qa.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrivateFactory:
    def mktemp(self, _name):
        path = OUT / "stack"
        path.mkdir(mode=0o700)
        return path


async def seed(stack) -> tuple[list[dict], dict]:
    names = ("operator", "approve", "reject", "approved", "active", "recipient")
    accounts = [
        {
            "username": f"w2_{name}",
            "account_id": f"acct_w2_{name}",
            "password": secrets.token_urlsafe(24),
            "role": name if name in ("operator", "recipient") else "issuer",
            "issuer_id": None if name in ("operator", "recipient") else f"iss_w2_{name}",
        }
        for name in names
    ]
    database = Database(stack["db_url"])
    try:
        async with database.session_factory() as db:
            db.add_all(
                [
                    AccountRow(
                        **{key: value for key, value in account.items() if key != "password"},
                        password_hash=password_hash(account["password"]),
                    )
                    for account in accounts
                ]
            )
            await db.commit()
    finally:
        await database.dispose()
    clients = {}
    metadata = {}
    try:
        for account in accounts:
            client = httpx.AsyncClient(base_url=stack["api"].url, trust_env=False, timeout=20)
            clients[account["username"]] = client
            response = await client.post(
                "/v1/auth/login",
                json={key: account[key] for key in ("username", "password")},
            )
            assert response.status_code == 200, "preparation login failed"
            client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        admin = clients["w2_operator"]
        for name in ("approved", "active"):
            issuer = clients[f"w2_{name}"]
            response = await issuer.post(
                "/v1/issuer-applications", json={"issuer_name": f"W2 Synthetic {name}"}
            )
            assert response.status_code == 201, "preparation application failed"
            application_id = response.json()["application_id"]
            metadata[f"{name}_application_id"] = application_id
            target = f"/v1/operator/issuer-applications/{application_id}"
            response = await admin.post(
                target + "/decision", json={"decision": "APPROVE", "reason": "D QA preparation"}
            )
            assert response.status_code == 200, "preparation decision failed"
            if name == "active":
                response = await admin.post(
                    target + "/activate",
                    json={"request_id": "req_w2_prepare_active", "reason": "D QA preparation"},
                )
                assert response.status_code == 200 and response.json()["status"] == "CONFIRMED"
                now = datetime.now(UTC).replace(microsecond=0)
                body = {
                    "request_id": "req_w2_prepare_key",
                    "reason": "D QA preparation",
                    "valid_from": (now - timedelta(minutes=1)).isoformat(),
                    "valid_until": (now + timedelta(days=7)).isoformat(),
                }
                response = await issuer.post("/v1/issuer/keys", json=body)
                assert response.status_code == 200 and response.json()["status"] == "CONFIRMED"
                metadata["confirmed_operation_id"] = response.json()["operation_id"]
                metadata["key_id"] = response.json()["target_id"]
                metadata["issuer_id"] = "iss_w2_active"
                # Real submitted transaction with lost RPC response, not an invented DB row.
                stack["rpc"].mode = "drop_send"
                response = await issuer.post(
                    "/v1/issuer/keys", json=body | {"request_id": "req_w2_prepare_unknown"}
                )
                assert response.status_code == 200 and response.json()["status"] == "UNKNOWN"
                metadata["unknown_operation_id"] = response.json()["operation_id"]
    finally:
        stack["rpc"].mode = None
        for client in clients.values():
            await client.aclose()
    return accounts, metadata


async def check_browser_database(stack) -> dict:
    database = Database(stack["db_url"])
    try:
        async with database.session_factory() as db:
            statuses = {
                row.issuer_id: row.status for row in await db.scalars(select(IssuerApplicationRow))
            }
            assert statuses["iss_w2_approve"] == "APPROVED_PENDING_CHAIN"
            assert statuses["iss_w2_reject"] == "REJECTED"
            # Browser period checking must not create a registration Operation.
            operations = list(await db.scalars(select(OperationRow)))
            assert all(row.request_id.startswith("req_w2_prepare_") for row in operations)
            return {"application_statuses": statuses, "operation_count": len(operations)}
    finally:
        await database.dispose()


def main() -> int:
    assert os.getenv("W2_BROWSER_QA") == "1", "W2_BROWSER_QA=1 is required"
    assert not OUT.exists(), "preserve existing QA output; use a new checkout"
    assert (ROOT / ".env").read_text() == "LLM_PROVIDER=mock\nOPENAI_MODEL=gpt-6-luna\n"
    OUT.mkdir(parents=True, mode=0o700)
    helper = recovery_module()
    resources = helper.stack.__wrapped__(PrivateFactory())
    web = None
    log = None
    result = {}
    try:
        stack = next(resources)
        accounts, metadata = asyncio.run(seed(stack))
        private_file(OUT / "accounts.json", json.dumps(accounts))
        port = free_port()
        metadata.update(
            api_url=stack["api"].url,
            web_url=f"http://127.0.0.1:{port}",
            chain_id=31337,
            source_commit_sha=helper.command("git", "rev-parse", "HEAD"),
            product_source_sha=helper.command("git", "rev-parse", "origin/phase/W2"),
            deployment=json.loads(stack["manifest"].read_text()),
            preparation="API-only seed; never full UI acceptance evidence",
        )
        private_file(OUT / "metadata.json", json.dumps(metadata))
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        env.update(
            ORIGINPROOF_API_ORIGIN=stack["api"].url,
            W2_WEB_URL=metadata["web_url"],
            W2_QA_DISPOSABLE="1",
            W2_QA_ACCOUNTS=str(OUT / "accounts.json"),
            W2_QA_METADATA=str(OUT / "metadata.json"),
            W2_BROWSER_OUTPUT=str(OUT / "test-results"),
            PLAYWRIGHT_JSON_OUTPUT_NAME=str(OUT / "browser-results.json"),
            LLM_PROVIDER="mock",
            OPENAI_MODEL="gpt-6-luna",
            pnpm_config_verify_deps_before_run="false",
        )
        # Next embeds the API rewrite at build time; each clean run builds its own source.
        helper.command("pnpm", "--filter", "originproof-demo-web", "build", env=env)
        private_file(OUT / "web.log", "")
        log = (OUT / "web.log").open("a")
        web = subprocess.Popen(
            [
                "pnpm",
                "--filter",
                "originproof-demo-web",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        with httpx.Client(timeout=1, trust_env=False) as client:
            helper.wait_ready(
                lambda: client.get(metadata["web_url"] + "/finals").status_code == 200
            )
        browser = subprocess.run(
            [
                "pnpm",
                "--filter",
                "originproof-demo-web",
                "test:e2e",
                "--config",
                "../../fixtures/finals/w2_browser_qa.config.ts",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = browser.stdout + browser.stderr
        for account in accounts:
            output = output.replace(account["password"], "[REDACTED]")
        private_file(OUT / "browser.log", output)
        # Sanitize even ignored machine reports if a failed locator ever included input.
        report_path = OUT / "browser-results.json"
        if report_path.exists():
            os.chmod(report_path, 0o600)
            report = report_path.read_text()
            for account in accounts:
                report = report.replace(account["password"], "[REDACTED]")
            report_path.write_text(report)
        result = {
            "browser_exit_code": browser.returncode,
            "db_check": asyncio.run(check_browser_database(stack)),
            "product_source_sha": metadata["product_source_sha"],
            "qa_source_sha": metadata["source_commit_sha"],
            "deployment": metadata["deployment"],
            "rpc_url": stack["rpc_url"],
            "web_url": metadata["web_url"],
            "source": "actual Chromium + HTTP + PostgreSQL + Anvil; no route mocks",
            "acceptance": "report browser projects separately; gaps do not become PASS",
        }
        print(output)
    finally:
        try:
            if web is not None:
                try:
                    os.killpg(web.pid, signal.SIGTERM)
                    web.wait(timeout=10)
                except ProcessLookupError:
                    web.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(web.pid, signal.SIGKILL)
                    web.wait(timeout=5)
        finally:
            if log is not None:
                log.close()
            resources.close()
            result["owned_resources_cleaned"] = True
            private_file(OUT / "summary.json", json.dumps(result, indent=2))
    return 0 if result.get("browser_exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
