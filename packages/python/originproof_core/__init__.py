"""Pure domain models and deterministic verification primitives for OriginProof."""

from .canonicalization import canonical_json_bytes, payload_hash
from .models import (
    CardPaymentNotice,
    CardPaymentNoticeCandidate,
    LifecycleStatus,
    ReasonCode,
    SignedProofEnvelope,
    VerificationResult,
    VerificationStatus,
)

__all__ = [
    "CardPaymentNotice",
    "CardPaymentNoticeCandidate",
    "LifecycleStatus",
    "ReasonCode",
    "SignedProofEnvelope",
    "VerificationResult",
    "VerificationStatus",
    "canonical_json_bytes",
    "payload_hash",
]
