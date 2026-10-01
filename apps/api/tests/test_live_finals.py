"""Opt-in disposable PostgreSQL + actual B Reader/Writer and Anvil; no browser claims."""

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain.writer import ChainOperationState
from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, Database, FinalsProofRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_core.finals import FinalsSignedProofEnvelope
from originproof_core.signatures import signature_matches
from sqlalchemy import select

pytestmark = pytest.mark.skipif(
    not all(
        os.getenv(name)
        for name in (
            "TEST_DATABASE_URL",
            "TEST_CHAIN_RPC_URL",
            "TEST_CHAIN_MANIFEST",
        )
    ),
    reason="disposable PostgreSQL/Anvil not configured",
)


async def test_live_two_types_signing_storage_and_comparison(tmp_path):
    suffix = uuid4().hex[:12]
    settings = Settings(
        database_url=os.environ["TEST_DATABASE_URL"],
        blockchain_rpc_url=os.environ["TEST_CHAIN_RPC_URL"],
        blockchain_manifest_path=os.environ["TEST_CHAIN_MANIFEST"],
        signer_directory=str(tmp_path / "signers"),
        finals_payment_issuer_id=f"iss_bank_{suffix}",
        finals_document_issuer_id=f"iss_office_{suffix}",
    )
    database = Database(settings.database_url)
    app = create_app(database=database, settings=settings)
    accounts = [
        AccountRow(
            account_id=f"acct_{role}_{suffix}",
            username=f"{role}_{suffix}",
            password_hash=password_hash("synthetic-local-password"),
            role="issuer" if role in ("bank", "office") else role,
            issuer_id=f"iss_{role}_{suffix}" if role in ("bank", "office") else None,
        )
        for role in ("operator", "bank", "office", "recipient")
    ]
    try:
        async with database.session_factory() as db:
            db.add_all(accounts)
            await db.commit()
        async with (
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as admin,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as bank,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as office,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as recipient,
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anonymous,
        ):
            for client, account in zip((admin, bank, office, recipient), accounts, strict=True):
                login = await client.post(
                    "/v1/auth/login",
                    json={
                        "username": account.username,
                        "password": "synthetic-local-password",
                    },
                )
                assert login.status_code == 200, login.text
                client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
            now = datetime.now(UTC).replace(microsecond=0)
            for client, kind in ((bank, "PAYMENT_REQUEST"), (office, "OFFICIAL_DOCUMENT")):
                application = await client.post(
                    "/v1/issuer-applications",
                    json={
                        "issuer_name": f"Synthetic {kind}",
                    },
                )
                assert application.status_code == 201, application.text
                app_id = application.json()["application_id"]
                assert (
                    await admin.post(
                        f"/v1/operator/issuer-applications/{app_id}/decision",
                        json={"decision": "APPROVE", "reason": "synthetic approval"},
                    )
                ).status_code == 200
                activation = await admin.post(
                    f"/v1/operator/issuer-applications/{app_id}/activate",
                    json={"request_id": f"req_activate_{kind}_{suffix}", "reason": "synthetic"},
                )
                assert activation.json()["status"] == "CONFIRMED", activation.text
                registration = await client.post(
                    "/v1/issuer/keys",
                    json={
                        "request_id": f"req_key_{kind}_{suffix}",
                        "reason": "synthetic",
                        "valid_from": (now - timedelta(minutes=1)).isoformat(),
                        "valid_until": (now + timedelta(days=1)).isoformat(),
                    },
                )
                assert registration.json()["status"] == "CONFIRMED", registration.text
                content = {"proof_type": kind}
                if kind == "PAYMENT_REQUEST":
                    content.update(
                        amount_minor=10000, currency="KRW", target_ref="synthetic invoice"
                    )
                else:
                    content.update(
                        institution_code="ORIGIN_MOCK_OFFICE",
                        document_type="Certificate",
                        document_number="SYNTHETIC-001",
                        version=1,
                    )
                body = {
                    "request_id": f"req_issue_{kind}_{suffix}",
                    "recipient_id": accounts[3].account_id,
                    "expires_at": (now + timedelta(days=2)).isoformat(),
                    "content": content,
                }
                first, second = await asyncio.gather(
                    *[client.post("/v2/issuer/proofs", json=body) for _ in range(2)]
                )
                assert first.status_code == second.status_code == 200, (first.text, second.text)
                assert first.json() == second.json()
                proof_id = first.json()["proof_id"]
                stored = (await recipient.get(f"/v2/proofs/{proof_id}/content")).json()
                envelope = FinalsSignedProofEnvelope.model_validate(stored["envelope"])
                reader = app.state.chain_management.reader(envelope.issuer_id)
                key = await reader.get_key(envelope.key_id)
                assert signature_matches(envelope, key.signer)
                assert (await anonymous.get(f"/v2/proofs/{proof_id}/content")).status_code == 401
                public = await anonymous.get(f"/v2/proofs/{proof_id}")
                assert "payload" not in public.json() and "recipient_salt" not in public.text
                query = {"request_id": f"req_verify_{suffix}"}
                result = await anonymous.post(f"/v2/proofs/{proof_id}/verify", json=query)
                assert result.json()["verification_status"] == "VERIFIED", result.text
                assert result.json()["lifecycle_status"] is None
                assert result.json()["checks"]["proof_status"] == "NOT_RUN"
                candidate = content.copy()
                candidate.pop("proof_type")
                result = await recipient.post(
                    f"/v2/proofs/{proof_id}/verify", json=query | {"candidate": candidate}
                )
                assert result.json()["scope"] == "FULL_COMPARISON", result.text
                field = "amount_minor" if kind == "PAYMENT_REQUEST" else "document_number"
                candidate[field] = 10001 if kind == "PAYMENT_REQUEST" else "CHANGED"
                result = await recipient.post(
                    f"/v2/proofs/{proof_id}/verify", json=query | {"candidate": candidate}
                )
                assert result.json()["verification_status"] == "TAMPERED", result.text
                async with database.session_factory() as db:
                    rows = list(
                        await db.scalars(
                            select(FinalsProofRow).where(
                                FinalsProofRow.account_id
                                == envelope.issuer_id.replace("iss_", "acct_")
                            )
                        )
                    )
                    assert len(rows) == 1

                old_key_id = envelope.key_id
                rotation = {
                    "request_id": f"req_rotate_{kind}_{suffix}",
                    "reason": "normal rotation",
                    "valid_from": (now - timedelta(minutes=1)).isoformat(),
                    "valid_until": (now + timedelta(days=1)).isoformat(),
                }
                rotated = await client.post("/v1/issuer/keys/rotate", json=rotation)
                assert rotated.json()["status"] == "CONFIRMED", rotated.text
                assert rotated.json()["action"] == "rotate_key"
                again = await client.post("/v1/issuer/keys/rotate", json=rotation)
                assert again.json()["operation_id"] == rotated.json()["operation_id"]
                subsequent = await client.post(
                    "/v2/issuer/proofs",
                    json=body | {"request_id": f"req_after_rotation_{kind}_{suffix}"},
                )
                assert subsequent.json()["key_id"] == rotated.json()["target_id"]
                assert subsequent.json()["key_id"] != old_key_id
                historical = await anonymous.post(f"/v2/proofs/{proof_id}/verify", json=query)
                assert historical.json()["verification_status"] == "VERIFIED"
                assert not historical.json()["reason_codes"]
                # A future registration must not take the current issuing selection.
                future = await client.post(
                    "/v1/issuer/keys",
                    json=rotation
                    | {
                        "request_id": f"req_future_key_{kind}_{suffix}",
                        "valid_from": (now + timedelta(hours=1)).isoformat(),
                        "valid_until": (now + timedelta(hours=2)).isoformat(),
                    },
                )
                assert future.json()["status"] == "CONFIRMED", future.text
                key_list = (await client.get("/v1/issuer/keys")).json()
                assert [k["key_id"] for k in key_list if k["selected"]] == [
                    rotated.json()["target_id"]
                ]
                # A real unauthorized contract submission must not switch selected key.
                writer = app.state.chain_management.writer
                original_prepare = writer.prepare_register_key

                async def unauthorized_prepare(*args, _prepare=original_prepare, **kwargs):
                    return await _prepare(
                        app.state.chain_management.manifest.roles["registry_admin"],
                        *args[1:],
                        **kwargs,
                    )

                writer.prepare_register_key = unauthorized_prepare
                try:
                    failed = await client.post(
                        "/v1/issuer/keys/rotate",
                        json=rotation | {"request_id": f"req_failed_rotate_{kind}_{suffix}"},
                    )
                    assert failed.json()["status"] == "FAILED", failed.text
                finally:
                    writer.prepare_register_key = original_prepare
                selected_keys = (await client.get("/v1/issuer/keys")).json()
                assert [k["key_id"] for k in selected_keys if k["selected"]] == [
                    rotated.json()["target_id"]
                ]
                original_confirm = writer.confirm_prepared

                async def defer_confirmation(prepared, tx_hash, _confirm=original_confirm):
                    result = await _confirm(prepared, tx_hash)
                    assert result.state == ChainOperationState.CONFIRMED
                    return replace(
                        result, state=ChainOperationState.UNKNOWN, error_code="STATE_NOT_CONFIRMED"
                    )

                writer.confirm_prepared = defer_confirmation
                try:
                    older = await client.post(
                        "/v1/issuer/keys/rotate",
                        json=rotation | {"request_id": f"req_older_unknown_{kind}_{suffix}"},
                    )
                    assert older.json()["status"] == "UNKNOWN", older.text
                finally:
                    writer.confirm_prepared = original_confirm
                newer = await client.post(
                    "/v1/issuer/keys/rotate",
                    json=rotation | {"request_id": f"req_newer_confirmed_{kind}_{suffix}"},
                )
                assert newer.json()["status"] == "CONFIRMED", newer.text
                recovered = await client.post(
                    f"/v1/operations/{older.json()['operation_id']}/recover"
                )
                assert recovered.json()["status"] == "CONFIRMED", recovered.text
                key_list = (await client.get("/v1/issuer/keys")).json()
                assert [k["key_id"] for k in key_list if k["selected"]] == [
                    newer.json()["target_id"]
                ]
                revoked = await client.post(
                    f"/v1/issuer/keys/{old_key_id}/revoke",
                    json={
                        "request_id": f"req_old_compromise_{kind}_{suffix}",
                        "reason": "synthetic compromise",
                    },
                )
                assert revoked.json()["status"] == "CONFIRMED", revoked.text
                historical = await anonymous.post(f"/v2/proofs/{proof_id}/verify", json=query)
                assert historical.json()["verification_status"] == "VERIFIED"
                assert "ISSUER_KEY_REVOKED" in historical.json()["reason_codes"]
    finally:
        await database.dispose()
