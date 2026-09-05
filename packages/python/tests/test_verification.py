from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from eth_keys import keys
from originproof_core import (
    CardPaymentNotice,
    CardPaymentNoticeCandidate,
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
    ReasonCode,
    SignedProofEnvelope,
    VerificationRequest,
    VerificationService,
    VerificationStatus,
    payload_hash,
    signing_digest,
)


class InMemoryProofRepository:
    def __init__(self, proof: SignedProofEnvelope) -> None:
        self.proof = proof

    async def get_proof(self, proof_id: str) -> SignedProofEnvelope | None:
        return self.proof if proof_id == self.proof.proof_id else None


class InMemoryBlockchainReader:
    def __init__(self, signer: str) -> None:
        self.issuer = IssuerRecord(
            issuer_id="iss_origin_mock_bank",
            status=IssuerTrustStatus.ACTIVE,
        )
        self.key = KeyRecord(
            key_id="key_origin_mock_bank_1",
            issuer_id=self.issuer.issuer_id,
            signer=signer,
            status=KeyTrustStatus.ACTIVE,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            valid_until=datetime(2027, 1, 1, tzinfo=UTC),
        )

    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None:
        return self.issuer if issuer_id == self.issuer.issuer_id else None

    async def get_key(self, key_id: str) -> KeyRecord | None:
        return self.key if key_id == self.key.key_id else None

    async def is_key_valid(self, key_id: str, at: datetime) -> bool:
        return key_id == self.key.key_id and self.key.valid_from <= at < self.key.valid_until


def signed_envelope() -> tuple[SignedProofEnvelope, str]:
    private_key = keys.PrivateKey(b"\x01" * 32)
    payload = CardPaymentNotice(
        issuer_name="Origin Mock Bank",
        masked_card="1234",
        amount_minor=154000,
        currency="KRW",
        merchant="ORIGIN CAFE",
        approved_at=datetime(2026, 9, 3, 3, 14, tzinfo=UTC),
        transaction_id="txn_demo_001",
    )
    unsigned = SignedProofEnvelope(
        proof_id="prf_demo_001",
        issuer_id="iss_origin_mock_bank",
        key_id="key_origin_mock_bank_1",
        chain_id=31337,
        app_domain="originproof.mvp",
        payload=payload,
        payload_hash=payload_hash(payload),
        issued_at=datetime(2026, 9, 3, 3, 14, tzinfo=UTC),
        nonce="n" * 16,
        signature="0x" + "00" * 65,
    )
    digest = bytes.fromhex(signing_digest(unsigned).removeprefix("0x"))
    signature = "0x" + private_key.sign_msg_hash(digest).to_bytes().hex()
    return (
        unsigned.model_copy(update={"signature": signature}),
        private_key.public_key.to_checksum_address(),
    )


def verification_request(
    envelope: SignedProofEnvelope, **candidate_updates: object
) -> VerificationRequest:
    candidate_data = {
        field: value
        for field, value in envelope.payload.model_dump().items()
        if field in CardPaymentNoticeCandidate.model_fields
    }
    candidate_data.update(
        proof_id=envelope.proof_id,
        confidence=0.99,
    )
    candidate_data.update(candidate_updates)
    candidate = CardPaymentNoticeCandidate(**candidate_data)
    return VerificationRequest(
        proof_id=envelope.proof_id,
        candidate=candidate,
        request_id="req_test_001",
    )


async def test_valid_signed_proof_is_verified() -> None:
    envelope, signer = signed_envelope()
    service = VerificationService(
        InMemoryProofRepository(envelope),
        InMemoryBlockchainReader(signer),
    )

    result = await service.verify(verification_request(envelope))

    assert result.verification_status is VerificationStatus.VERIFIED
    assert result.reason_codes == []
    assert result.checks["signature"] == "PASS"


async def test_amount_tampering_is_reported_without_ai_authenticity_decision() -> None:
    envelope, signer = signed_envelope()
    service = VerificationService(
        InMemoryProofRepository(envelope),
        InMemoryBlockchainReader(signer),
    )

    result = await service.verify(verification_request(envelope, amount_minor=1540000))

    assert result.verification_status is VerificationStatus.TAMPERED
    assert result.reason_codes == [ReasonCode.AMOUNT_MISMATCH]
    assert result.checks["candidate_match"] == "FAIL"


async def test_payload_hash_mismatch_is_tampered() -> None:
    envelope, signer = signed_envelope()
    altered = envelope.model_copy(update={"payload_hash": "0x" + "ff" * 32})
    service = VerificationService(
        InMemoryProofRepository(altered),
        InMemoryBlockchainReader(signer),
    )

    result = await service.verify(verification_request(altered))

    assert result.verification_status is VerificationStatus.TAMPERED
    assert result.reason_codes == [ReasonCode.PAYLOAD_HASH_MISMATCH]


async def test_signature_mismatch_is_tampered() -> None:
    envelope, signer = signed_envelope()
    altered = envelope.model_copy(update={"nonce": "x" * 16})
    service = VerificationService(
        InMemoryProofRepository(altered),
        InMemoryBlockchainReader(signer),
    )

    result = await service.verify(verification_request(altered))

    assert result.verification_status is VerificationStatus.TAMPERED
    assert result.reason_codes == [ReasonCode.INVALID_SIGNATURE]


async def test_malformed_signature_is_tampered_instead_of_raising() -> None:
    envelope, signer = signed_envelope()
    altered = envelope.model_copy(update={"signature": "0x" + "00" * 65})
    service = VerificationService(
        InMemoryProofRepository(altered),
        InMemoryBlockchainReader(signer),
    )

    result = await service.verify(verification_request(altered))

    assert result.verification_status is VerificationStatus.TAMPERED
    assert result.reason_codes == [ReasonCode.INVALID_SIGNATURE]


def test_golden_fixture_matches_python_signing_contract() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "fixtures/golden/card_payment_notice_signing_v1.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload = CardPaymentNotice.model_validate(fixture["payload"])
    signing = fixture["signing_payload"]
    envelope = SignedProofEnvelope(
        proof_id=signing["proof_id"],
        issuer_id=signing["issuer_id"],
        key_id=signing["key_id"],
        proof_type=signing["proof_type"],
        schema_version=signing["schema_version"],
        signature_scheme=signing["signature_scheme"],
        chain_id=signing["chain_id"],
        app_domain=signing["app_domain"],
        payload=payload,
        payload_hash=fixture["payload_hash"],
        subject_binding_hash=signing["subject_binding_hash"],
        issued_at=signing["issued_at"],
        expires_at=signing["expires_at"],
        nonce=signing["nonce"],
        single_use=signing["single_use"],
        metadata_hash=signing["metadata_hash"],
        signature="0x" + "00" * 65,
    )

    assert payload_hash(payload) == fixture["payload_hash"]
    assert signing_digest(envelope) == fixture["signing_digest"]
