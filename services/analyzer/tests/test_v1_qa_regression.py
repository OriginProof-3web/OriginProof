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


@pytest.mark.parametrize("filename", ["card_notice_valid.json", "card_notice_amount_tampered.json"])
async def test_existing_card_fixture_through_real_verification_core(filename):
    golden = json.loads((ROOT / "golden/card_payment_notice_signing_v1.json").read_text())
    case = json.loads((ROOT / "mvp" / filename).read_text())
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
    candidate = CardPaymentNoticeCandidate.model_validate(
        {
            **{k: v for k, v in case.items() if k in CardPaymentNoticeCandidate.model_fields},
            "confidence": 1.0,
        }
    )
    result = await VerificationService(repository, reader).verify(
        VerificationRequest(
            proof_id=case["proof_id"],
            candidate=candidate,
            request_id="req_qa_v1_" + Path(filename).stem,
        )
    )
    assert result.verification_status.value == case["expected_verification_status"]
    assert result.lifecycle_status.value == case["expected_lifecycle_status"]
    assert [r.value for r in result.reason_codes] == case["expected_reason_codes"]
