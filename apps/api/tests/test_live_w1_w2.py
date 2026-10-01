"""Opt-in PostgreSQL check for the W1/W2 C foundation.

Run with TEST_DATABASE_URL pointing to a disposable migrated database.
"""

import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, Database
from originproof_api.main import create_app
from originproof_api.operations import reserve_operation
from originproof_api.settings import Settings

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="test DB not configured")


async def test_postgres_login_application_and_operation_flow() -> None:
    url = os.environ["TEST_DATABASE_URL"]
    database = Database(url)
    app = create_app(database=database, settings=Settings(database_url=url))
    suffix = uuid4().hex[:12]
    password = "synthetic-test-password"
    operator = AccountRow(
        account_id=f"acct_operator_{suffix}",
        username=f"operator_{suffix}",
        password_hash=password_hash(password),
        role="operator",
    )
    issuer_a = AccountRow(
        account_id=f"acct_issuer_a_{suffix}",
        username=f"issuer_a_{suffix}",
        password_hash=password_hash(password),
        role="issuer",
        issuer_id=f"iss_a_{suffix}",
    )
    issuer_b = AccountRow(
        account_id=f"acct_issuer_b_{suffix}",
        username=f"issuer_b_{suffix}",
        password_hash=password_hash(password),
        role="issuer",
        issuer_id=f"iss_b_{suffix}",
    )
    try:
        async with database.session_factory() as db:
            db.add_all([operator, issuer_a, issuer_b])
            await db.commit()

        transport = ASGITransport(app=app)
        async with (
            AsyncClient(transport=transport, base_url="http://test") as a,
            AsyncClient(transport=transport, base_url="http://test") as b,
            AsyncClient(transport=transport, base_url="http://test") as admin,
        ):

            async def sign_in(client: AsyncClient, username: str) -> str:
                response = await client.post(
                    "/v1/auth/login", json={"username": username, "password": password}
                )
                assert response.status_code == 200, response.text
                return response.json()["csrf_token"]

            csrf_a = await sign_in(a, issuer_a.username)
            await sign_in(b, issuer_b.username)
            csrf_admin = await sign_in(admin, operator.username)

            no_csrf = await a.post("/v1/issuer-applications", json={"issuer_name": "Mock A"})
            assert no_csrf.status_code == 403
            created = await a.post(
                "/v1/issuer-applications",
                json={"issuer_name": "Mock A"},
                headers={"X-CSRF-Token": csrf_a},
            )
            assert created.status_code == 201, created.text
            application_id = created.json()["application_id"]
            assert created.json()["status"] == "PENDING_REVIEW"
            assert (await b.get("/v1/issuer-applications/mine")).json() is None

            decided = await admin.post(
                f"/v1/operator/issuer-applications/{application_id}/decision",
                json={"decision": "APPROVE", "reason": "synthetic review"},
                headers={"X-CSRF-Token": csrf_admin},
            )
            assert decided.status_code == 200, decided.text
            assert decided.json()["status"] == "APPROVED_PENDING_CHAIN"
            assert (await a.get("/v1/issuer-applications/mine")).json()["status"] == (
                "APPROVED_PENDING_CHAIN"
            )
            assert (await b.get("/v1/audit-events")).json() == []
            assert len((await a.get("/v1/audit-events")).json()) == 1

            request_id = f"req_{suffix}"
            first = await reserve_operation(
                database.session_factory,
                issuer_a,
                "ISSUER_ACTIVATE",
                request_id,
                {"issuer_id": issuer_a.issuer_id},
            )
            same = await reserve_operation(
                database.session_factory,
                issuer_a,
                "ISSUER_ACTIVATE",
                request_id,
                {"issuer_id": issuer_a.issuer_id},
            )
            assert same.operation_id == first.operation_id
            with pytest.raises(HTTPException) as conflict:
                await reserve_operation(
                    database.session_factory,
                    issuer_a,
                    "ISSUER_ACTIVATE",
                    request_id,
                    {"issuer_id": issuer_b.issuer_id},
                )
            assert conflict.value.status_code == 409
            assert (await a.get(f"/v1/operations/{first.operation_id}")).status_code == 200
            assert (await b.get(f"/v1/operations/{first.operation_id}")).status_code == 404
            assert (await admin.get(f"/v1/operations/{first.operation_id}")).status_code == 200

            logged_out = await a.post("/v1/auth/logout", headers={"X-CSRF-Token": csrf_a})
            assert logged_out.status_code == 200
            assert (await a.get("/v1/auth/me")).status_code == 401
    finally:
        await database.dispose()
