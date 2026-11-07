"""Opt-in HTTP + PostgreSQL + actual B adapter/Anvil, disposable environment only."""

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain.writer import ChainOperationState
from originproof_api.accounts import password_hash
from originproof_api.chain_management import ChainManagement
from originproof_api.database import AccountRow, Database, IssuerApplicationRow, OperationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings

pytestmark = pytest.mark.skipif(
    not (
        os.getenv("TEST_DATABASE_URL")
        and os.getenv("TEST_CHAIN_RPC_URL")
        and os.getenv("TEST_CHAIN_MANIFEST")
    ),
    reason="disposable DB/Anvil not configured",
)


async def test_live_approval_keys_failure_and_restart(tmp_path):
    settings = Settings(
        database_url=os.environ["TEST_DATABASE_URL"],
        blockchain_rpc_url=os.environ["TEST_CHAIN_RPC_URL"],
        blockchain_manifest_path=os.environ["TEST_CHAIN_MANIFEST"],
        signer_directory=str(tmp_path / "signers"),
    )
    database = Database(settings.database_url)
    app = create_app(database=database, settings=settings)
    suffix = uuid4().hex[:12]
    password = "synthetic-disposable-password"
    accounts = [
        AccountRow(
            account_id=f"acct_{role}_{suffix}",
            username=f"{role}_{suffix}",
            password_hash=password_hash(password),
            role="operator" if role == "operator" else "issuer",
            issuer_id=None if role == "operator" else f"iss_{role}_{suffix}",
        )
        for role in ("operator", "issuer_a", "issuer_b")
    ]
    try:
        async with database.session_factory() as db:
            db.add_all(accounts)
            await db.commit()
        async with (
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as admin,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as a,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as b,
        ):
            for client, account in zip((admin, a, b), accounts, strict=True):
                login = await client.post(
                    "/v1/auth/login", json={"username": account.username, "password": password}
                )
                assert login.status_code == 200, login.text
                client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
            applications = []
            for client, name in ((a, "Synthetic A"), (b, "Synthetic B")):
                submitted = await client.post("/v1/issuer-applications", json={"issuer_name": name})
                assert submitted.status_code == 201, submitted.text
                application_id = submitted.json()["application_id"]
                applications.append(application_id)
                decision = await admin.post(
                    f"/v1/operator/issuer-applications/{application_id}/decision",
                    json={"decision": "APPROVE", "reason": "synthetic review"},
                )
                assert decision.status_code == 200, decision.text
            body = {"request_id": f"req_approve_{suffix}", "reason": "synthetic activation"}
            path = f"/v1/operator/issuer-applications/{applications[0]}/activate"
            responses = await asyncio.gather(
                admin.post(path, json=body), admin.post(path, json=body)
            )
            assert all(
                r.status_code == 200 and r.json()["status"] == "CONFIRMED" for r in responses
            ), [r.text for r in responses]
            assert responses[0].json()["operation_id"] == responses[1].json()["operation_id"]
            assert (await admin.post(path, json=body | {"reason": "changed"})).status_code == 409
            assert (await a.get("/v1/issuer/status")).json()["status"] == "ACTIVE"
            # Real send occurs, but its response/hash is lost; restart must scan fixed nonce.
            manager = app.state.chain_management
            original_submit = manager.writer.submit_prepared

            async def lose_hash(prepared):
                result = await original_submit(prepared)
                assert result.state == ChainOperationState.SUBMITTED
                return replace(
                    result,
                    state=ChainOperationState.UNKNOWN,
                    tx_hash=None,
                    error_code="SUBMISSION_UNKNOWN",
                )

            manager.writer.submit_prepared = lose_hash
            uncertain = await admin.post(
                f"/v1/operator/issuer-applications/{applications[1]}/activate",
                json=body | {"request_id": f"req_lost_{suffix}"},
            )
            assert uncertain.status_code == 200 and uncertain.json()["status"] == "UNKNOWN", (
                uncertain.text
            )
            operation_id = uncertain.json()["operation_id"]
            async with database.session_factory() as db:
                row = await db.get(OperationRow, operation_id)
                assert row.tx_hash is None and row.recovery_reference["nonce"] is not None
                assert (
                    await db.get(IssuerApplicationRow, applications[1])
                ).status == "APPROVED_PENDING_CHAIN"
            app.state.chain_management = ChainManagement(database, settings)
            recovered = await admin.post(f"/v1/operations/{operation_id}/recover")
            assert recovered.status_code == 200 and recovered.json()["status"] == "CONFIRMED", (
                recovered.text
            )
            assert recovered.json()["chain_evidence"]["confirmation_count"] >= 1
            now = datetime.now(UTC).replace(microsecond=0)
            key_body = {
                "request_id": f"req_key_{suffix}",
                "reason": "synthetic key",
                "valid_from": now.isoformat(),
                "valid_until": (now + timedelta(days=1)).isoformat(),
            }
            registered = await a.post("/v1/issuer/keys", json=key_body)
            assert registered.status_code == 200 and registered.json()["status"] == "CONFIRMED", (
                registered.text
            )
            same = await a.post("/v1/issuer/keys", json=key_body)
            assert same.json()["operation_id"] == registered.json()["operation_id"]
            keys = (await a.get("/v1/issuer/keys")).json()
            assert len(keys) == 1 and keys[0]["status"] == "ACTIVE" and keys[0]["selected"]
            key_id = keys[0]["key_id"]
            assert "secret_ref" not in str(keys) and "private" not in str(keys)
            assert (await b.get(f"/v1/issuer/keys/{key_id}")).status_code == 404
            assert (await b.post(f"/v1/issuer/keys/{key_id}/revoke", json=body)).status_code == 404
            assert (
                await a.post(f"/v1/operator/issuers/{accounts[1].issuer_id}/suspend", json=body)
            ).status_code == 403
            suspend = await admin.post(
                f"/v1/operator/issuers/{accounts[1].issuer_id}/suspend", json=body
            )
            assert suspend.json()["status"] == "CONFIRMED", suspend.text
            denied = await a.post(
                "/v1/issuer/keys", json=key_body | {"request_id": f"req_denied_{suffix}"}
            )
            assert denied.status_code == 409
            reactivated = await admin.post(
                f"/v1/operator/issuers/{accounts[1].issuer_id}/reactivate", json=body
            )
            assert reactivated.json()["status"] == "CONFIRMED", reactivated.text
            rotated = await a.post(
                "/v1/issuer/keys", json=key_body | {"request_id": f"req_rotate_{suffix}"}
            )
            assert rotated.json()["status"] == "CONFIRMED", rotated.text
            keys = (await a.get("/v1/issuer/keys")).json()
            assert len(keys) == 2 and sum(k["selected"] for k in keys) == 1
            assert all(k["status"] == "ACTIVE" for k in keys)
            revoked = await a.post(f"/v1/issuer/keys/{key_id}/revoke", json=body)
            assert revoked.json()["status"] == "CONFIRMED", revoked.text
            assert (await a.get(f"/v1/issuer/keys/{key_id}")).json()["status"] == "REVOKED"
            # The existing contract rejects a second distinct revoke, never report success.
            failed = await a.post(
                f"/v1/issuer/keys/{key_id}/revoke", json=body | {"request_id": f"req_fail_{suffix}"}
            )
            assert failed.json()["status"] == "FAILED", failed.text
            assert failed.json()["chain_evidence"]["error_code"] == "CHAIN_REVERTED"
    finally:
        await database.dispose()
