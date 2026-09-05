from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from originproof_core import CardPaymentNotice, SignedProofEnvelope, payload_hash, signing_digest
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.signatures import signing_payload

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "fixtures" / "golden" / "card_payment_notice_signing_v1.json"


def main() -> None:
    payload = CardPaymentNotice(
        issuer_name="Origin Mock Bank",
        masked_card="1234",
        amount_minor=154000,
        currency="KRW",
        merchant="ORIGIN CAFE",
        approved_at=datetime(2026, 9, 3, 3, 14, tzinfo=UTC),
        transaction_id="txn_demo_001",
    )
    envelope = SignedProofEnvelope(
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
    fixture = {
        "generated_by": "scripts/generate_golden_fixture.py",
        "identifier_hashing": "keccak256(utf8(identifier))",
        "payload": json.loads(canonical_json_bytes(payload)),
        "payload_canonical_json": canonical_json_bytes(payload).decode("utf-8"),
        "payload_hash": envelope.payload_hash,
        "signing_payload": json.loads(canonical_json_bytes(signing_payload(envelope))),
        "signing_canonical_json": canonical_json_bytes(signing_payload(envelope)).decode("utf-8"),
        "signing_digest": signing_digest(envelope),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
