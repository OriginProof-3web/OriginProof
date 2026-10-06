"""Generate public synthetic v2 vectors, never a runtime signing key."""

import json
from datetime import UTC, datetime
from pathlib import Path

from eth_keys import keys
from originproof_core import canonical_json_bytes, payload_hash, signing_digest
from originproof_core.finals import (
    FinalsSignedProofEnvelope,
    OfficialDocument,
    PaymentRequest,
    beneficiary_binding,
    recipient_binding,
    target_binding,
)
from originproof_core.signatures import signing_payload

ROOT = Path(__file__).resolve().parents[1]


def envelopes():
    # Public test vector scalar; must never be loaded by runtime signer storage.
    key = keys.PrivateKey(bytes.fromhex("11" * 32))
    for kind, issuer in (
        ("PAYMENT_REQUEST", "iss_origin_mock_bank"),
        ("OFFICIAL_DOCUMENT", "iss_origin_mock_office"),
    ):
        proof_id = "prf_golden_" + kind.lower()
        binding = recipient_binding(proof_id, "synthetic-test-recipient", "22" * 32, 31337)
        payload = (
            PaymentRequest(
                amount_minor=154000,
                currency="KRW",
                payer_binding=binding,
                beneficiary_binding=beneficiary_binding(issuer, 31337),
                target_hash=target_binding("synthetic-request-001"),
            )
            if kind == "PAYMENT_REQUEST"
            else OfficialDocument(
                institution_code="ORIGIN_MOCK_OFFICE",
                document_type="CERTIFICATE",
                document_number="SYNTHETIC-001",
                subject_token=binding,
                version=1,
            )
        )
        envelope = FinalsSignedProofEnvelope(
            proof_id=proof_id,
            issuer_id=issuer,
            key_id="key_golden_v2",
            proof_type=kind,
            schema_version="2.0.0",
            signature_scheme="ECDSA_SECP256K1_KECCAK256_V1",
            chain_id=31337,
            app_domain="originproof.finals",
            payload=payload,
            payload_hash=payload_hash(payload),
            subject_binding_hash=binding,
            issued_at=datetime(2026, 10, 1, tzinfo=UTC),
            expires_at=datetime(2026, 10, 2, tzinfo=UTC),
            nonce="33" * 16,
            single_use=kind == "PAYMENT_REQUEST",
            signature="0x" + "00" * 65,
        )
        envelope.signature = (
            "0x" + key.sign_msg_hash(bytes.fromhex(signing_digest(envelope)[2:])).to_bytes().hex()
        )
        yield envelope, key.public_key.to_checksum_address()


def main():
    for envelope, signer in envelopes():
        vector = {
            "purpose": "synthetic public signing interoperability vector; not production",
            "generated_by": "scripts/generate_finals_golden.py",
            "signer": signer,
            "envelope": envelope.model_dump(mode="json"),
            "payload_canonical_json": canonical_json_bytes(envelope.payload).decode(),
            "signing_canonical_json": canonical_json_bytes(signing_payload(envelope)).decode(),
            "signing_digest": signing_digest(envelope),
        }
        path = ROOT / "fixtures/golden" / (envelope.proof_type.lower() + "_signing_v2.json")
        path.write_text(json.dumps(vector, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
