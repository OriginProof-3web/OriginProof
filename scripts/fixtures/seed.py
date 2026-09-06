from __future__ import annotations

import json
import os
from pathlib import Path

from eth_keys import keys
from originproof_api.database import Database
from originproof_api.repositories import SqlAlchemyProofRepository
from originproof_api.settings import Settings
from originproof_core import CardPaymentNotice, SignedProofEnvelope, payload_hash, signing_digest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "mvp"
OUTPUT = ROOT / "build" / "seed_manifest.json"
PRIVATE_KEY_PATH = ROOT / "build" / "mock_issuer_private_key.hex"


def read_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _load_or_create_private_key() -> keys.PrivateKey:
    """Create a local-only key for synthetic development data, never for production use."""
    PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PRIVATE_KEY_PATH.exists():
        return keys.PrivateKey(bytes.fromhex(PRIVATE_KEY_PATH.read_text(encoding="utf-8").strip()))

    private_key = keys.PrivateKey(os.urandom(32))
    PRIVATE_KEY_PATH.write_text(private_key.to_hex()[2:] + "\n", encoding="utf-8")
    PRIVATE_KEY_PATH.chmod(0o600)
    return private_key


async def seed() -> dict[str, object]:
    valid = read_fixture("card_notice_valid.json")
    tampered = read_fixture("card_notice_amount_tampered.json")
    if valid["proof_id"] != tampered["proof_id"]:
        raise SystemExit("fixtures must use the same proof_id")
    if valid["amount_minor"] == tampered["amount_minor"]:
        raise SystemExit("tampered fixture must change amount_minor")

    payload_fields = CardPaymentNotice.model_fields
    payload = CardPaymentNotice.model_validate(
        {field: valid[field] for field in payload_fields if field in valid}
    )
    private_key = _load_or_create_private_key()
    unsigned_envelope = SignedProofEnvelope(
        proof_id=str(valid["proof_id"]),
        issuer_id="iss_origin_mock_bank",
        key_id="key_origin_mock_bank_001",
        chain_id=31337,
        app_domain="originproof.mvp",
        payload=payload,
        payload_hash=payload_hash(payload),
        issued_at=payload.approved_at,
        nonce="seeded_originproof_demo_nonce_001",
        signature="0x" + "00" * 65,
    )
    signed_envelope = unsigned_envelope.model_copy(
        update={
            "signature": "0x"
            + private_key.sign_msg_hash(
                bytes.fromhex(signing_digest(unsigned_envelope).removeprefix("0x"))
            )
            .to_bytes()
            .hex()
        }
    )

    database = Database(os.environ.get("SEED_DATABASE_URL", Settings().database_url))
    try:
        await SqlAlchemyProofRepository(database.session_factory).upsert(signed_envelope)
    finally:
        await database.dispose()

    return {
        "issuer": "Origin Mock Bank",
        "issuer_id": signed_envelope.issuer_id,
        "key_id": signed_envelope.key_id,
        "signer": private_key.public_key.to_checksum_address(),
        "proof_id": signed_envelope.proof_id,
        "payload_hash": signed_envelope.payload_hash,
        "fixtures": ["card_notice_valid.json", "card_notice_amount_tampered.json"],
        "source": "synthetic",
    }


async def async_main() -> int:
    manifest = await seed()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(async_main()))
