"""Opt-in W1 browser/HTTP QA against an explicitly disposable migrated PostgreSQL DB."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from originproof_api.accounts import password_hash
from originproof_api.database import (
    AccountRow,
    AuditEventRow,
    Database,
    IssuerApplicationRow,
    SessionRow,
)
from sqlalchemy import delete, select, update

ROOT = Path(__file__).resolve().parents[2]


async def main() -> None:
    if os.getenv("W1_QA_DISPOSABLE") != "1":
        raise SystemExit("W1_QA_DISPOSABLE=1 is required; never use a preserved database")
    database = Database(os.environ["TEST_DATABASE_URL"])
    api_url = os.environ["W1_LIVE_API_URL"]
    os.environ["W1_LIVE_BASE_URL"]  # Require an independently started web from the same SHA.
    suffix = uuid4().hex[:10]
    password = secrets.token_urlsafe(24)
    accounts = {}
    for role in ("issuer_a", "issuer_b", "operator", "recipient", "self_operator"):
        accounts[role] = {
            "account_id": f"acct_qa_{role}_{suffix}",
            "username": f"qa_{role}_{suffix}",
            "role": "operator" if role.endswith("operator") else role.split("_")[0],
            "issuer_id": f"iss_qa_{role}_{suffix}" if role.startswith("issuer") else None,
            "password": password,
        }
    accounts["self_operator"]["issuer_id"] = f"iss_qa_self_{suffix}"
    accounts["self_operator"]["application_id"] = f"app_qa_self_{suffix}"
    ids = [a["account_id"] for a in accounts.values()]
    try:
        async with database.session_factory() as db:
            db.add_all(
                AccountRow(
                    **{k: v for k, v in a.items() if k not in {"password", "application_id"}},
                    password_hash=password_hash(password),
                )
                for a in accounts.values()
            )
            own = accounts["self_operator"]
            db.add(
                IssuerApplicationRow(
                    application_id=own["application_id"],
                    issuer_id=own["issuer_id"],
                    applicant_account_id=own["account_id"],
                    issuer_name="Self approval adversarial",
                    status="PENDING_REVIEW",
                )
            )
            await db.commit()
        env = os.environ | {"W1_QA_ACCOUNTS": json.dumps(accounts)}
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "pnpm",
                "--filter",
                "originproof-demo-web",
                "exec",
                "playwright",
                "test",
                "e2e/w1-live.spec.ts",
                "--workers=1",
            ],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if result.returncode:
            raise SystemExit(result.returncode)
        async with httpx.AsyncClient(base_url=api_url) as client:
            login = await client.post(
                "/v1/auth/login",
                json={
                    "username": accounts["recipient"]["username"],
                    "password": password,
                },
            )
            assert login.status_code == 200
            cookie = login.headers["set-cookie"].lower()
            assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=28800" in cookie
            async with database.session_factory() as db:
                await db.execute(
                    update(SessionRow)
                    .where(SessionRow.account_id == accounts["recipient"]["account_id"])
                    .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )
                await db.commit()
            assert (await client.get("/v1/auth/me")).status_code == 401
        async with database.session_factory() as db:
            for role, status in (("issuer_a", "APPROVED_PENDING_CHAIN"), ("issuer_b", "REJECTED")):
                row = await db.scalar(
                    select(IssuerApplicationRow).where(
                        IssuerApplicationRow.applicant_account_id == accounts[role]["account_id"]
                    )
                )
                assert row is not None and row.status == status
            events = list(
                await db.scalars(
                    select(AuditEventRow).where(AuditEventRow.actor_account_id.in_(ids))
                )
            )
            assert len(events) == 2
        print("W1 live DB checks: approval/rejection, two audit records, expired session: PASS")
    finally:
        async with database.session_factory() as db:
            for model, column in (
                (AuditEventRow, AuditEventRow.actor_account_id),
                (IssuerApplicationRow, IssuerApplicationRow.applicant_account_id),
                (SessionRow, SessionRow.account_id),
                (AccountRow, AccountRow.account_id),
            ):
                await db.execute(delete(model).where(column.in_(ids)))
            await db.commit()
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
