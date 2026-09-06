from datetime import datetime

from originproof_core import canonical_json_bytes, payload_hash


def test_canonical_json_normalizes_unicode_key_order_and_utc() -> None:
    first = {
        "merchant": " ORIGIN CAFE ",
        "approved_at": datetime.fromisoformat("2026-09-03T12:14:00+09:00"),
        "issuer_name": "Origin Mock Bank",
    }
    second = {
        "issuer_name": "Origin Mock Bank",
        "approved_at": "2026-09-03T03:14:00Z",
        "merchant": "ORIGIN CAFE",
    }

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert payload_hash(first) == payload_hash(second)


def test_payload_hash_uses_ethereum_keccak() -> None:
    assert payload_hash({"value": "OriginProof"}) == (
        "0x7f46594c44796107d643b6e5039ac52c099522b42cd89057346add468fb86cb2"
    )
