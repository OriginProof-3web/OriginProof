import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from originproof_core import (
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
    LifecycleStatus,
    payload_hash,
    signer_address,
    signing_digest,
)
from originproof_core.finals import FinalsSignedProofEnvelope, recipient_binding
from originproof_core.finals_verification import evaluate_finals
from pydantic import ValidationError

GOLDEN = Path(__file__).resolve().parents[3] / "fixtures/golden"


@pytest.fixture(params=["payment_request", "official_document"])
def vector(request):
    data = json.loads((GOLDEN / f"{request.param}_signing_v2.json").read_text())
    envelope = FinalsSignedProofEnvelope.model_validate(data["envelope"])
    return envelope, data


def evaluate(envelope, signer, **updates):
    options = dict(
        request_id="req_test",
        chain_id=31337,
        issuer=IssuerRecord(issuer_id=envelope.issuer_id, status=IssuerTrustStatus.ACTIVE),
        key=KeyRecord(
            key_id=envelope.key_id,
            issuer_id=envelope.issuer_id,
            signer=signer,
            status=KeyTrustStatus.ACTIVE,
            valid_from=envelope.issued_at,
            valid_until=envelope.expires_at,
        ),
        now=envelope.issued_at + timedelta(hours=1),
    )
    options.update(updates)
    return evaluate_finals(envelope, **options)


def test_golden_signature_and_w3_scope(vector):
    envelope, data = vector
    assert payload_hash(envelope.payload) == envelope.payload_hash
    assert signing_digest(envelope) == data["signing_digest"]
    assert signer_address(envelope) == data["signer"]
    result = evaluate(envelope, data["signer"])
    assert result.verification_status == "VERIFIED"
    assert result.lifecycle_status is None and result.checks["proof_status"] == "NOT_RUN"
    expired = evaluate(
        envelope, data["signer"], now=envelope.expires_at, proof_states={LifecycleStatus.ACTIVE}
    )
    assert expired.verification_status == "VERIFIED" and expired.lifecycle_status == "EXPIRED"


def test_contract_period_binding_and_single_use(vector):
    envelope, _ = vector
    for update in (
        dict(single_use=not envelope.single_use),
        dict(nonce="weak"),
        dict(subject_binding_hash="0x" + "ff" * 32),
        dict(expires_at=envelope.issued_at),
        dict(issued_at=datetime(2026, 10, 1)),
        dict(issued_at=envelope.issued_at.replace(microsecond=1)),
    ):
        with pytest.raises(ValidationError):
            FinalsSignedProofEnvelope.model_validate(envelope.model_dump() | update)
    assert recipient_binding("prf_a", "token", "11" * 32, 31337) != recipient_binding(
        "prf_b", "token", "11" * 32, 31337
    )


def test_failure_order_comparison_and_current_status(vector):
    envelope, data = vector
    network = evaluate(envelope, data["signer"], chain_id=1)
    assert network.reason_codes == ["NETWORK_MISMATCH"]
    assert network.checks["signature"] == "NOT_RUN"
    invalid = evaluate(
        envelope.model_copy(update={"signature": "0x" + "00" * 65}),
        data["signer"],
        proof_states={LifecycleStatus.PROOF_REVOKED},
    )
    assert invalid.verification_status == "TAMPERED" and invalid.lifecycle_status is None
    key = KeyRecord(
        key_id=envelope.key_id,
        issuer_id=envelope.issuer_id,
        signer=data["signer"],
        status=KeyTrustStatus.REVOKED,
        valid_from=envelope.issued_at,
        valid_until=envelope.expires_at,
    )
    revoked = evaluate(
        envelope,
        data["signer"],
        key=key,
        proof_states={LifecycleStatus.CONSUMED, LifecycleStatus.PROOF_REVOKED},
    )
    assert revoked.verification_status == "VERIFIED"
    assert revoked.lifecycle_status == "PROOF_REVOKED"
    assert "ISSUER_KEY_REVOKED" in revoked.reason_codes
    partial = evaluate(envelope, data["signer"], candidate={})
    assert partial.verification_status == "INCONCLUSIVE" and partial.scope == "PARTIAL_COMPARISON"
    fields = envelope.payload.model_dump()
    complete = evaluate(envelope, data["signer"], candidate=fields)
    assert complete.verification_status == "VERIFIED" and complete.scope == "FULL_COMPARISON"
    field = "amount_minor" if "amount_minor" in fields else "version"
    mismatch = evaluate(envelope, data["signer"], candidate={field: fields[field] + 1})
    assert mismatch.verification_status == "TAMPERED"


def test_previous_key_expiry_does_not_revoke_past_signature(vector):
    envelope, data = vector
    key = KeyRecord(
        key_id=envelope.key_id,
        issuer_id=envelope.issuer_id,
        signer=data["signer"],
        status="ACTIVE",
        valid_from=envelope.issued_at,
        valid_until=envelope.issued_at + timedelta(minutes=1),
    )
    result = evaluate(envelope, data["signer"], key=key, proof_states={LifecycleStatus.ACTIVE})
    assert result.verification_status == "VERIFIED" and result.lifecycle_status == "ACTIVE"
