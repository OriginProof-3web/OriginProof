"""Version 2 contracts. Version 1 card models and endpoint remain unchanged."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .canonicalization import payload_hash
from .models import LifecycleStatus, SignatureScheme, VerificationStatus

HASH = r"^0x[0-9a-f]{64}$"


class FinalsProofType(StrEnum):
    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    OFFICIAL_DOCUMENT = "OFFICIAL_DOCUMENT"


class VerificationScope(StrEnum):
    PROOF_ONLY = "PROOF_ONLY"
    FULL_COMPARISON = "FULL_COMPARISON"
    PARTIAL_COMPARISON = "PARTIAL_COMPARISON"


class CheckState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    UNAVAILABLE = "UNAVAILABLE"


class FinalsReasonCode(StrEnum):
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    PAYLOAD_HASH_MISMATCH = "PAYLOAD_HASH_MISMATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    FIELD_MISMATCH = "FIELD_MISMATCH"
    PROOF_EXPIRED = "PROOF_EXPIRED"
    PROOF_NOT_FOUND = "PROOF_NOT_FOUND"
    ISSUER_NOT_FOUND = "ISSUER_NOT_FOUND"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    DOMAIN_MISMATCH = "DOMAIN_MISMATCH"
    NETWORK_MISMATCH = "NETWORK_MISMATCH"
    KEY_NOT_FOUND = "KEY_NOT_FOUND"
    KEY_TIME_INVALID = "KEY_TIME_INVALID"
    INPUT_INCOMPLETE = "INPUT_INCOMPLETE"
    SUBJECT_BINDING_MISMATCH = "SUBJECT_BINDING_MISMATCH"
    PROOF_REVOKED = "PROOF_REVOKED"
    ISSUER_KEY_REVOKED = "ISSUER_KEY_REVOKED"
    ISSUER_SUSPENDED = "ISSUER_SUSPENDED"


class PaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_minor: int = Field(gt=0, strict=True)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    payer_binding: str = Field(pattern=HASH)
    beneficiary_binding: str = Field(pattern=HASH)
    target_hash: str = Field(pattern=HASH)


class OfficialDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution_code: str = Field(min_length=1, max_length=120)
    document_type: str = Field(min_length=1, max_length=120)
    document_number: str = Field(min_length=1, max_length=120)
    subject_token: str = Field(pattern=HASH)
    version: int = Field(gt=0, strict=True)

    @field_validator("institution_code", "document_type", "document_number")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class FinalsSignedProofEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proof_id: str = Field(pattern=r"^prf_[A-Za-z0-9_-]+$")
    issuer_id: str = Field(pattern=r"^iss_[A-Za-z0-9_-]+$")
    key_id: str = Field(pattern=r"^key_[A-Za-z0-9_-]+$")
    proof_type: FinalsProofType
    schema_version: Literal["2.0.0"]
    signature_scheme: SignatureScheme
    chain_id: int = Field(gt=0, strict=True)
    app_domain: Literal["originproof.finals"]
    payload: PaymentRequest | OfficialDocument
    payload_hash: str = Field(pattern=HASH)
    subject_binding_hash: str = Field(pattern=HASH)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(pattern=r"^[0-9a-f]{32,64}$")
    single_use: bool = Field(strict=True)
    metadata_hash: str | None = Field(default=None, pattern=HASH)
    signature: str = Field(pattern=r"^0x[0-9a-f]{130}$")

    @field_validator("issued_at", "expires_at")
    @classmethod
    def chain_seconds(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None or value.microsecond:
            raise ValueError("timezone and whole seconds required")
        return value

    @model_validator(mode="after")
    def consistent_contract(self) -> Self:
        payment = self.proof_type == FinalsProofType.PAYMENT_REQUEST
        if payment != isinstance(self.payload, PaymentRequest) or self.single_use != payment:
            raise ValueError("payload/single_use must match proof_type")
        if self.issued_at >= self.expires_at:
            raise ValueError("issued_at must precede expires_at")
        binding = self.payload.payer_binding if payment else self.payload.subject_token
        if binding != self.subject_binding_hash:
            raise ValueError("payload recipient binding must match envelope")
        if payment and self.payload.beneficiary_binding != beneficiary_binding(
            self.issuer_id, self.chain_id, self.app_domain
        ):
            raise ValueError("beneficiary binding must match issuer/domain/network")
        return self


class FinalsVerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(pattern=r"^vsn_[A-Za-z0-9_-]+$")
    verification_status: VerificationStatus
    lifecycle_status: LifecycleStatus | None
    scope: VerificationScope
    reason_codes: list[FinalsReasonCode] = Field(default_factory=list)
    checks: dict[str, CheckState]
    verified_at: datetime
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]+$")


def recipient_binding(
    proof_id: str,
    recipient_token: str,
    salt: str,
    chain_id: int,
    app_domain: str = "originproof.finals",
) -> str:
    if len(salt) != 64 or any(c not in "0123456789abcdef" for c in salt):
        raise ValueError("recipient salt must be 32 bytes of lowercase hex")
    if not recipient_token or not proof_id or chain_id <= 0:
        raise ValueError("binding inputs required")
    return payload_hash(
        {
            "binding_domain": "originproof.recipient.v1",
            "app_domain": app_domain,
            "chain_id": chain_id,
            "proof_id": proof_id,
            "recipient_token": recipient_token,
            "salt": salt,
        }
    )


def beneficiary_binding(
    issuer_id: str,
    chain_id: int,
    app_domain: str = "originproof.finals",
) -> str:
    return payload_hash(
        {
            "binding_domain": "originproof.beneficiary.v1",
            "app_domain": app_domain,
            "chain_id": chain_id,
            "issuer_id": issuer_id,
        }
    )


def target_binding(target_ref: str) -> str:
    if not target_ref.strip():
        raise ValueError("target reference required")
    return payload_hash({"target_domain": "originproof.target.v1", "target_ref": target_ref})


def representative_lifecycle(states: set[LifecycleStatus]) -> LifecycleStatus:
    for status in (
        LifecycleStatus.PROOF_REVOKED,
        LifecycleStatus.ISSUER_KEY_REVOKED,
        LifecycleStatus.ISSUER_SUSPENDED,
        LifecycleStatus.CONSUMED,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.ACTIVE,
    ):
        if status in states:
            return status
    return LifecycleStatus.ACTIVE
