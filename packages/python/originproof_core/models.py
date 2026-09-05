from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProofType(StrEnum):
    CARD_PAYMENT_NOTICE = "CARD_PAYMENT_NOTICE"


class SignatureScheme(StrEnum):
    ECDSA_SECP256K1_KECCAK256_V1 = "ECDSA_SECP256K1_KECCAK256_V1"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    NOT_REGISTERED = "NOT_REGISTERED"
    TAMPERED = "TAMPERED"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"
    PROOF_REVOKED = "PROOF_REVOKED"
    ISSUER_SUSPENDED = "ISSUER_SUSPENDED"
    ISSUER_KEY_REVOKED = "ISSUER_KEY_REVOKED"


class ReasonCode(StrEnum):
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    PAYLOAD_HASH_MISMATCH = "PAYLOAD_HASH_MISMATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    FIELD_MISMATCH = "FIELD_MISMATCH"
    PROOF_EXPIRED = "PROOF_EXPIRED"
    PROOF_NOT_FOUND = "PROOF_NOT_FOUND"
    ISSUER_NOT_FOUND = "ISSUER_NOT_FOUND"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    LOW_OCR_CONFIDENCE = "LOW_OCR_CONFIDENCE"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    MALFORMED_INPUT = "MALFORMED_INPUT"


class CardPaymentNotice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuer_name: str = Field(min_length=1, max_length=120)
    masked_card: str = Field(pattern=r"^\d{4}$")
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    merchant: str = Field(min_length=1, max_length=160)
    approved_at: datetime
    transaction_id: str = Field(min_length=1, max_length=120)

    @field_validator("issuer_name", "merchant", "transaction_id")
    @classmethod
    def reject_empty_normalized_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class CardPaymentNoticeCandidate(BaseModel):
    """Candidate fields extracted from user input; this model has no authenticity result."""

    model_config = ConfigDict(extra="forbid")

    issuer_name: str | None = None
    masked_card: str | None = Field(default=None, pattern=r"^\d{4}$")
    amount_minor: int | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    merchant: str | None = None
    approved_at: datetime | None = None
    transaction_id: str | None = None
    proof_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)


class SignedProofEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_id: str = Field(pattern=r"^prf_[A-Za-z0-9_-]+$")
    issuer_id: str = Field(pattern=r"^iss_[A-Za-z0-9_-]+$")
    key_id: str = Field(pattern=r"^key_[A-Za-z0-9_-]+$")
    proof_type: ProofType = ProofType.CARD_PAYMENT_NOTICE
    schema_version: str = "1.0.0"
    signature_scheme: SignatureScheme = SignatureScheme.ECDSA_SECP256K1_KECCAK256_V1
    chain_id: int = Field(gt=0)
    app_domain: str = Field(min_length=3, max_length=120)
    payload: CardPaymentNotice
    payload_hash: str = Field(pattern=r"^0x[0-9a-f]{64}$")
    subject_binding_hash: str | None = Field(default=None, pattern=r"^0x[0-9a-f]{64}$")
    issued_at: datetime
    expires_at: datetime | None = None
    nonce: str = Field(min_length=16, max_length=256)
    single_use: bool = True
    metadata_hash: str | None = Field(default=None, pattern=r"^0x[0-9a-f]{64}$")
    signature: str = Field(pattern=r"^0x[0-9a-f]+$")


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(pattern=r"^vsn_[A-Za-z0-9_-]+$")
    verification_status: VerificationStatus
    lifecycle_status: LifecycleStatus | None = None
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    checks: dict[str, str]
    verified_at: datetime
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]+$")


class VerificationRequest(BaseModel):
    """Untrusted candidate fields plus an identifier for the server-side signed proof."""

    model_config = ConfigDict(extra="forbid")

    proof_id: str = Field(pattern=r"^prf_[A-Za-z0-9_-]+$")
    candidate: CardPaymentNoticeCandidate
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]+$")
