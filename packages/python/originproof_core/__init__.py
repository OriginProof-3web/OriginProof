"""Pure domain models and deterministic verification primitives for OriginProof."""

from .canonicalization import canonical_json_bytes, payload_hash
from .models import (
    CardPaymentNotice,
    CardPaymentNoticeCandidate,
    LifecycleStatus,
    ReasonCode,
    SignatureScheme,
    SignedProofEnvelope,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)
from .ports import (
    BlockchainReader,
    DependencyUnavailableError,
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
    ProofRepository,
)
from .signatures import signer_address, signing_digest
from .verification import VerificationService

__all__ = [
    "CardPaymentNotice",
    "CardPaymentNoticeCandidate",
    "BlockchainReader",
    "DependencyUnavailableError",
    "IssuerRecord",
    "IssuerTrustStatus",
    "KeyRecord",
    "KeyTrustStatus",
    "LifecycleStatus",
    "ReasonCode",
    "SignedProofEnvelope",
    "SignatureScheme",
    "ProofRepository",
    "signer_address",
    "signing_digest",
    "VerificationRequest",
    "VerificationResult",
    "VerificationService",
    "VerificationStatus",
    "canonical_json_bytes",
    "payload_hash",
]
