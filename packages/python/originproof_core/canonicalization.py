from __future__ import annotations

import json
import unicodedata
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from Crypto.Hash import keccak
from pydantic import BaseModel


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python", exclude_none=False))
    if isinstance(value, Enum):
        return _normalize(value.value)
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.strip())
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical UTF-8 JSON shared by Python and Solidity Golden Fixtures."""
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def payload_hash(value: Any) -> str:
    """Ethereum Keccak-256, not NIST SHA3-256."""
    digest = keccak.new(digest_bits=256)
    digest.update(canonical_json_bytes(value))
    return f"0x{digest.hexdigest()}"
