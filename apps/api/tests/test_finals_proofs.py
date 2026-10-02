"""Real SQLite/HTTP/signatures; synthetic chain is replaced by opt-in live tests."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import test_w2_chain_management as w2_tests
from httpx import ASGITransport, AsyncClient
from originproof_api.database import (
    AccountRow,
    FinalsProofRow,
    IssuerKeyRow,
    RecipientTokenRow,
    SessionRow,
)
from originproof_api.finals_proofs import optional_identity
from originproof_core import DependencyUnavailableError
from originproof_core.ports import IssuerRecord, IssuerTrustStatus, KeyRecord, KeyTrustStatus
from sqlalchemy import select
from sqlalchemy.orm import Session

AsyncSession = w2_tests.AsyncSession
context = w2_tests.context


@pytest.fixture
async def finals(context):
    client, manager, selected, accounts, engine = context
    manager.settings.finals_payment_issuer_id = "iss_a"
    manager.settings.finals_document_issuer_id = "iss_b"
    recipients = [
        AccountRow(
            account_id=f"acct_recipient_{i}",
            username=f"recipient_{i}",
            role="recipient",
            password_hash="unused",
        )
        for i in (1, 2)
    ]
    with Session(engine, expire_on_commit=False) as db:
        db.add_all(recipients)
        db.commit()
    manager.rpc_failure = False

    class Reader:
        async def get_issuer(self, identifier):
            if manager.rpc_failure:
                raise DependencyUnavailableError("synthetic RPC outage")
            return IssuerRecord(issuer_id=identifier, status=IssuerTrustStatus.ACTIVE)

        async def get_key(self, identifier):
            if manager.rpc_failure:
                raise DependencyUnavailableError("synthetic RPC outage")
            with Session(engine) as db:
                row = db.get(IssuerKeyRow, identifier)
                if not row:
                    return None
                return KeyRecord(
                    key_id=row.key_id,
                    issuer_id=row.issuer_id,
                    signer=row.signer,
                    valid_from=datetime.fromtimestamp(row.valid_from, UTC),
                    valid_until=datetime.fromtimestamp(row.valid_until, UTC),
                    status=KeyTrustStatus.REVOKED
                    if row.status == "REVOKED"
                    else KeyTrustStatus.ACTIVE,
                )

    manager.reader = lambda _: Reader()

    async def optional_session():
        return selected[0], SessionRow(csrf_token="csrf")

    client._transport.app.dependency_overrides[optional_identity] = optional_session
    now = datetime.now(UTC).replace(microsecond=0)
    for issuer in accounts[1:]:
        selected[0] = issuer
        response = await client.post(
            "/v1/issuer/keys",
            json={
                "request_id": "req_initial_key",
                "reason": "synthetic initial key",
                "valid_from": (now - timedelta(minutes=1)).isoformat(),
                "valid_until": (now + timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 200, response.text
    selected[0] = accounts[1]
    yield client, manager, selected, accounts, recipients, engine


def body(kind="PAYMENT_REQUEST", request_id="req_issue"):
    content = {"proof_type": kind}
    if kind == "PAYMENT_REQUEST":
        content.update(amount_minor=10000, currency="KRW", target_ref="synthetic-invoice-1")
    else:
        content.update(
            institution_code="ORIGIN_MOCK_OFFICE",
            document_type="Certificate",
            document_number="SYNTHETIC-001",
            version=1,
        )
    return {
        "request_id": request_id,
        "recipient_id": "acct_recipient_1",
        "expires_at": (datetime.now(UTC).replace(microsecond=0) + timedelta(days=2)).isoformat(),
        "content": content,
    }


async def test_issue_both_types_idempotency_and_scopes(finals):
    client, _, selected, accounts, recipients, engine = finals
    for kind, issuer in zip(("PAYMENT_REQUEST", "OFFICIAL_DOCUMENT"), accounts[1:], strict=True):
        selected[0] = issuer
        request = body(kind)
        first, second = await asyncio.gather(
            *[client.post("/v2/issuer/proofs", json=request) for _ in range(2)]
        )
        assert first.status_code == second.status_code == 200, (first.text, second.text)
        assert first.json() == second.json()
        proof_id = first.json()["proof_id"]
        assert (
            await client.post(
                "/v2/issuer/proofs", json=request | {"recipient_id": "acct_recipient_2"}
            )
        ).status_code == 409
        assert len((await client.get("/v2/issuer/proofs")).json()) == 1
        envelope = (await client.get(f"/v2/proofs/{proof_id}/content")).json()["envelope"]
        assert envelope["single_use"] == (kind == "PAYMENT_REQUEST")
        assert "recipient_salt" not in str(envelope) and "secret_ref" not in str(envelope)
        selected[0] = recipients[0]
        payload = request["content"] | {}
        payload.pop("proof_type")
        result = await client.post(
            f"/v2/proofs/{proof_id}/verify",
            json={
                "request_id": "req_compare",
                "candidate": payload,
            },
        )
        assert result.json()["verification_status"] == "VERIFIED", result.text
        assert result.json()["scope"] == "FULL_COMPARISON"
        assert result.json()["checks"]["proof_status"] == "NOT_RUN"
        assert result.json()["lifecycle_status"] is None
        field = "amount_minor" if kind == "PAYMENT_REQUEST" else "document_number"
        changed = 999 if kind == "PAYMENT_REQUEST" else "CHANGED"
        result = await client.post(
            f"/v2/proofs/{proof_id}/verify",
            json={
                "request_id": "req_tamper",
                "candidate": payload | {field: changed},
            },
        )
        assert result.json()["verification_status"] == "TAMPERED", result.text
        result = await client.post(
            f"/v2/proofs/{proof_id}/verify",
            json={
                "request_id": "req_partial",
                "candidate": {},
            },
        )
        assert result.json()["scope"] == "PARTIAL_COMPARISON"
        assert result.json()["verification_status"] == "INCONCLUSIVE"
        selected[0] = recipients[1]
        assert (await client.get(f"/v2/proofs/{proof_id}/content")).status_code == 404
        assert (
            await client.post(
                f"/v2/proofs/{proof_id}/verify",
                json={
                    "request_id": "req_forbidden",
                    "candidate": payload,
                },
            )
        ).status_code == 404
        selected[0] = accounts[2] if issuer == accounts[1] else accounts[1]
        assert (await client.get(f"/v2/proofs/{proof_id}/content")).status_code == 404
    with Session(engine) as db:
        assert len(db.scalars(select(FinalsProofRow)).all()) == 2
        token = db.get(RecipientTokenRow, recipients[0].account_id)
        salts = [row.recipient_salt for row in db.scalars(select(FinalsProofRow))]
        assert len(set(salts)) == 2 and len(token.token) == 64


async def test_public_read_rpc_failure_binding_and_restart(finals):
    client, manager, selected, _, recipients, engine = finals
    created = await client.post("/v2/issuer/proofs", json=body())
    proof_id = created.json()["proof_id"]
    app = client._transport.app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anonymous:
        # Auth override is removed to exercise real anonymous access.
        overrides = app.dependency_overrides.copy()
        app.dependency_overrides.clear()
        try:
            public = await anonymous.get(f"/v2/proofs/{proof_id}")
            assert public.status_code == 200 and "payload" not in public.json()
            assert (await anonymous.get(f"/v2/proofs/{proof_id}/content")).status_code == 401
            verified = await anonymous.post(
                f"/v2/proofs/{proof_id}/verify",
                json={
                    "request_id": "req_public",
                },
            )
            assert verified.json()["verification_status"] == "VERIFIED"
            assert verified.json()["scope"] == "PROOF_ONLY"
            assert (
                await anonymous.post(
                    f"/v2/proofs/{proof_id}/verify",
                    json={
                        "request_id": "req_compare",
                        "candidate": {},
                    },
                )
            ).status_code == 401
        finally:
            app.dependency_overrides.update(overrides)
    manager.rpc_failure = True
    result = await client.post(f"/v2/proofs/{proof_id}/verify", json={"request_id": "req_rpc"})
    assert result.json()["verification_status"] == "INCONCLUSIVE"
    assert result.json()["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
    manager.rpc_failure = False
    selected[0] = recipients[0]
    with Session(engine) as db:
        db.get(RecipientTokenRow, recipients[0].account_id).token = "ff" * 32
        db.commit()
    assert (await client.get(f"/v2/proofs/{proof_id}/content")).status_code == 404
    missing = await client.post("/v2/proofs/prf_missing/verify", json={"request_id": "req_missing"})
    assert missing.json()["verification_status"] == "NOT_REGISTERED"


async def test_issuance_rejects_untrusted_inputs_and_storage_failure(finals, monkeypatch):
    client, manager, _, _, _, engine = finals
    request = body()
    assert (
        await client.post("/v2/issuer/proofs", json=request, headers={"X-CSRF-Token": "wrong"})
    ).status_code == 403
    assert (
        await client.post("/v2/issuer/proofs", json=body("OFFICIAL_DOCUMENT"))
    ).status_code == 403
    assert (
        await client.post("/v2/issuer/proofs", json=request | {"recipient_id": "acct_operator"})
    ).status_code == 422
    assert (
        await client.post(
            "/v2/issuer/proofs",
            json=request | {"content": request["content"] | {"amount_minor": True}},
        )
    ).status_code == 422
    manager.active = False
    assert (await client.post("/v2/issuer/proofs", json=request)).status_code == 409
    manager.active = True
    original = AsyncSession.commit

    async def fail_commit(self):
        raise RuntimeError("synthetic commit failure")

    monkeypatch.setattr(AsyncSession, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="commit failure"):
        await client.post("/v2/issuer/proofs", json=request)
    monkeypatch.setattr(AsyncSession, "commit", original)
    with Session(engine) as db:
        assert not db.scalar(select(FinalsProofRow))
        assert not db.scalar(select(RecipientTokenRow))
    assert (await client.post("/v2/issuer/proofs", json=request)).status_code == 200


async def test_missing_signer_expired_key_and_document_input(finals):
    client, manager, selected, accounts, _, engine = finals
    selected[0] = accounts[2]
    request = body("OFFICIAL_DOCUMENT")
    assert (
        await client.post(
            "/v2/issuer/proofs",
            json=request | {"content": request["content"] | {"document_number": "   "}},
        )
    ).status_code == 422
    assert (
        await client.post(
            "/v2/issuer/proofs",
            json=request | {"content": request["content"] | {"institution_code": "OTHER_OFFICE"}},
        )
    ).status_code == 422
    assert (
        await client.post(
            "/v2/issuer/proofs", json=request | {"expires_at": "2020-01-01T00:00:00Z"}
        )
    ).status_code == 422
    with Session(engine) as db:
        key = db.scalar(select(IssuerKeyRow).where(IssuerKeyRow.issuer_id == "iss_b"))
        key.valid_until = int(datetime.now(UTC).timestamp())
        secret_ref = key.secret_ref
        db.commit()
    assert (await client.post("/v2/issuer/proofs", json=request)).status_code == 409
    with Session(engine) as db:
        key = db.scalar(select(IssuerKeyRow).where(IssuerKeyRow.issuer_id == "iss_b"))
        key.valid_until += 3600
        db.commit()
    from pathlib import Path

    (Path(manager.settings.signer_directory) / secret_ref).unlink()
    response = await client.post("/v2/issuer/proofs", json=request)
    assert response.status_code == 409 and response.json()["detail"] == "SIGNER_UNAVAILABLE"


async def test_invalid_stored_proof_and_redeployment_are_not_verified(finals):
    client, manager, _, _, _, engine = finals
    created = await client.post("/v2/issuer/proofs", json=body())
    proof_id = created.json()["proof_id"]
    with Session(engine) as db:
        row = db.get(FinalsProofRow, proof_id)
        original = row.envelope.copy()
        row.envelope = original | {"payload_hash": "0x" + "ff" * 32}
        db.commit()
    result = await client.post(f"/v2/proofs/{proof_id}/verify", json={"request_id": "req_hash"})
    assert result.json()["verification_status"] == "TAMPERED"
    assert result.json()["checks"]["issuer"] == "NOT_RUN"
    with Session(engine) as db:
        row = db.get(FinalsProofRow, proof_id)
        row.envelope = original | {"app_domain": "originproof.mvp"}
        db.commit()
    result = await client.post(f"/v2/proofs/{proof_id}/verify", json={"request_id": "req_domain"})
    assert result.json()["verification_status"] == "INCONCLUSIVE"
    with Session(engine) as db:
        db.get(FinalsProofRow, proof_id).envelope = original
        db.commit()
    manager.manifest.deployment_id = "dep_" + "ff" * 32
    result = await client.post(f"/v2/proofs/{proof_id}/verify", json={"request_id": "req_redeploy"})
    assert result.json()["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
