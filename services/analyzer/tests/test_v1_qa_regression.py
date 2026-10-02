"""D's independent card fixture -> real core regression, with in-memory ports."""

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from eth_keys import keys
from originproof_core import (
    CardPaymentNoticeCandidate,
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
    SignedProofEnvelope,
    VerificationRequest,
    VerificationService,
    signing_digest,
)

ROOT = Path(__file__).resolve().parents[3] / "fixtures"


@pytest.fixture
def v1_verifier():
    golden = json.loads((ROOT / "golden/card_payment_notice_signing_v1.json").read_text())
    envelope = SignedProofEnvelope.model_validate(
        {
            **golden["signing_payload"],
            "payload": golden["payload"],
            "signature": "0x" + "00" * 65,
        }
    )
    assert signing_digest(envelope) == golden["signing_digest"]
    # Ephemeral test signer stays in memory; C's Golden is never rewritten.
    key = keys.PrivateKey(secrets.token_bytes(32))
    signature = key.sign_msg_hash(bytes.fromhex(golden["signing_digest"].removeprefix("0x")))
    envelope = envelope.model_copy(update={"signature": "0x" + signature.to_bytes().hex()})
    repository = AsyncMock()
    repository.get_proof.return_value = envelope
    reader = AsyncMock()
    reader.get_issuer.return_value = IssuerRecord(
        issuer_id=envelope.issuer_id, status=IssuerTrustStatus.ACTIVE
    )
    reader.get_key.return_value = KeyRecord(
        key_id=envelope.key_id,
        issuer_id=envelope.issuer_id,
        signer=key.public_key.to_checksum_address(),
        status=KeyTrustStatus.ACTIVE,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=datetime(2027, 1, 1, tzinfo=UTC),
    )
    reader.is_key_valid.return_value = True
    return VerificationService(repository, reader), envelope


@pytest.mark.parametrize("filename", ["card_notice_valid.json", "card_notice_amount_tampered.json"])
async def test_existing_card_fixture_through_real_verification_core(filename, v1_verifier):
    case = json.loads((ROOT / "mvp" / filename).read_text())
    candidate = CardPaymentNoticeCandidate.model_validate(
        {
            **{k: v for k, v in case.items() if k in CardPaymentNoticeCandidate.model_fields},
            "confidence": 1.0,
        }
    )
    verifier, _ = v1_verifier
    result = await verifier.verify(
        VerificationRequest(
            proof_id=case["proof_id"],
            candidate=candidate,
            request_id="req_qa_v1_" + Path(filename).stem,
        )
    )
    assert result.verification_status.value == case["expected_verification_status"]
    assert result.lifecycle_status.value == case["expected_lifecycle_status"]
    assert [r.value for r in result.reason_codes] == case["expected_reason_codes"]


@pytest.mark.parametrize(
    "case",
    json.loads((ROOT / "mvp/analyzer_safety_cases.json").read_text())["cases"],
    ids=lambda case: case["id"],
)
async def test_high_confidence_wrong_candidate_still_fails_comparison(case, v1_verifier):
    verifier, envelope = v1_verifier
    candidate = CardPaymentNoticeCandidate.model_validate(
        {
            **envelope.payload.model_dump(),
            "proof_id": envelope.proof_id,
            **case["candidate_changes"],
            "confidence": 0.999,
        }
    )
    result = await verifier.verify(
        VerificationRequest(
            proof_id=envelope.proof_id, candidate=candidate, request_id="req_safety_high_confidence"
        )
    )
    # This legacy status is a deterministic candidate mismatch, not proof of its cause.
    assert result.verification_status.value == "TAMPERED"
    assert [reason.value for reason in result.reason_codes] == [case["legacy_comparison_reason"]]
    # Legacy mismatch returns before signature/Registry checks; ACTIVE is not evidence of those.
    assert "signature" not in result.checks
    assert "issuer" not in result.checks


async def test_observed_amount_mismatch_is_not_hidden_by_missing_currency(v1_verifier):
    verifier, envelope = v1_verifier
    candidate = CardPaymentNoticeCandidate.model_validate(
        {
            **envelope.payload.model_dump(),
            "proof_id": envelope.proof_id,
            "amount_minor": envelope.payload.amount_minor + 1,
            "currency": None,
            "missing_fields": ["currency"],
            "confidence": 1.0,
        }
    )
    result = await verifier.verify(
        VerificationRequest(
            proof_id=envelope.proof_id,
            candidate=candidate,
            request_id="req_safety_missing_mismatch",
        )
    )
    assert result.verification_status.value == "TAMPERED"
    assert [reason.value for reason in result.reason_codes] == ["AMOUNT_MISMATCH"]


async def test_legacy_null_candidate_limitation_is_reproducible(v1_verifier):
    verifier, envelope = v1_verifier
    result = await verifier.verify(
        VerificationRequest(
            proof_id=envelope.proof_id,
            candidate=CardPaymentNoticeCandidate(confidence=1.0),
            request_id="req_safety_null_limitation",
        )
    )
    # Diagnostic of C's unchanged v1 contract, NOT acceptance of complete artifact matching.
    # The A/C handoff requires a separate scope result and confirmation enforcement.
    assert result.verification_status.value == "VERIFIED"
    assert result.checks["candidate_match"] == "PASS"
