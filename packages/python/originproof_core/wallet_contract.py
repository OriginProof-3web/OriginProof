"""Shared v5 preparation models; importing these does not enable an API or deployment."""

from __future__ import annotations

import base64
import unicodedata
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


def uint256_value(value: str) -> str:
    if int(value) >= 2**256:
        raise ValueError("value must fit uint256")
    return value


def nonzero_address(value: str) -> str:
    if int(value, 16) == 0:
        raise ValueError("address must not be zero")
    return value.lower()


REVISION = "v5-shared-0.1"
SAFE_INTEGER = 2**53 - 1
Hex32 = Annotated[str, Field(pattern=r"^0x[0-9a-f]{64}$")]
Address = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$"), AfterValidator(nonzero_address)]
Seconds = Annotated[int, Field(strict=True, ge=0, le=SAFE_INTEGER)]
Version = Annotated[int, Field(strict=True, ge=1, le=SAFE_INTEGER)]
Uint256 = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,77})$"), AfterValidator(uint256_value)]
RequestId = Annotated[str, Field(pattern=r"^req_[A-Za-z0-9_-]{1,124}$")]
Signature = Annotated[str, Field(pattern=r"^0x[0-9a-f]{130}$")]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    @field_validator("*", mode="after")
    @classmethod
    def utf8_strings(cls, value):
        if isinstance(value, str):
            value.encode("utf-8")
        return value

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_codes(cls, value):
        if isinstance(value, dict):
            for name in (
                "action",
                "originalHashAlgorithm",
                "protectedHashAlgorithm",
                "original_hash_algorithm",
                "protected_hash_algorithm",
            ):
                if isinstance(value.get(name), bool):
                    raise ValueError("protocol codes must be integers, not booleans")
        return value

    @field_validator("official_url", check_fields=False)
    @classmethod
    def https_link(cls, value):
        if value is not None:
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or any(ord(c) < 32 or ord(c) == 127 for c in value)
            ):
                raise ValueError(
                    "official_url must be an HTTPS URL without credentials or controls"
                )
        return value


class WalletDomain(ContractModel):
    name: Literal["OriginProof"] = "OriginProof"
    version: Literal["1"] = "1"
    chain_id: Uint256 = Field(alias="chainId")
    verifying_contract: Address = Field(alias="verifyingContract")

    @field_validator("chain_id")
    @classmethod
    def valid_chain(cls, value: str) -> str:
        if not 0 < int(value) < 2**256:
            raise ValueError("chainId must fit a positive uint256")
        return value


class PaymentContent(ContractModel):
    notice_type: Literal["PAYMENT_REQUEST"]
    amount_minor: Annotated[int, Field(strict=True, gt=0, le=SAFE_INTEGER)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    payee_bank_name: Annotated[str, Field(min_length=1, max_length=120)]
    payee_account_number: Annotated[str, Field(pattern=r"^[0-9]{6,32}$")]
    payee_account_holder: Annotated[str, Field(min_length=1, max_length=120)]
    payment_purpose: Annotated[str, Field(min_length=1, max_length=500)]
    due_at: Seconds
    official_url: Annotated[str, Field(max_length=2048)] | None = None

    @field_validator(
        "currency",
        "payee_bank_name",
        "payee_account_holder",
        "payment_purpose",
        "official_url",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            return unicodedata.normalize("NFC", value.strip())
        return value

    @field_validator("payee_account_number", mode="before")
    @classmethod
    def clean_account(cls, value):
        return value.replace(" ", "").replace("-", "") if isinstance(value, str) else value

    @field_validator("payee_bank_name", "payee_account_holder", "payment_purpose")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be blank")
        return value


class OfficialContent(ContractModel):
    notice_type: Literal["OFFICIAL_DOCUMENT"]
    institution_code: Annotated[str, Field(min_length=1, max_length=120)]
    document_type: Annotated[str, Field(min_length=1, max_length=120)]
    document_number: Annotated[str, Field(min_length=1, max_length=120)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    official_url: Annotated[str, Field(max_length=2048)] | None = None

    @field_validator(
        "institution_code",
        "document_type",
        "document_number",
        "title",
        "summary",
        "official_url",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            return unicodedata.normalize("NFC", value.strip())
        return value


Content = Annotated[PaymentContent | OfficialContent, Field(discriminator="notice_type")]


class PublishMessage(ContractModel):
    action: Literal[1] = 1
    issuer_id: Hex32 = Field(alias="issuerId")
    doc_key: Hex32 = Field(alias="docKey")
    document_id: Hex32 = Field(alias="documentId")
    version: Version
    key_id: Hex32 = Field(alias="keyId")
    original_hash: Hex32 = Field(alias="originalHash")
    protected_hash: Hex32 = Field(alias="protectedHash")
    content_schema: Hex32 = Field(alias="contentSchema")
    signature_schema: Hex32 = Field(alias="signatureSchema")
    original_hash_algorithm: Literal[1] = Field(default=1, alias="originalHashAlgorithm")
    protected_hash_algorithm: Literal[1] = Field(default=1, alias="protectedHashAlgorithm")
    issued_at: Seconds = Field(alias="issuedAt")
    expires_at: Seconds = Field(alias="expiresAt")
    nonce: Uint256
    deadline: Seconds

    @model_validator(mode="after")
    def time_window(self) -> Self:
        if not self.issued_at < self.deadline <= self.expires_at:
            raise ValueError("issuedAt < deadline <= expiresAt is required")
        return self


class RevokeMessage(ContractModel):
    action: Literal[2] = 2
    issuer_id: Hex32 = Field(alias="issuerId")
    doc_key: Hex32 = Field(alias="docKey")
    document_id: Hex32 = Field(alias="documentId")
    version: Version
    key_id: Hex32 = Field(alias="keyId")
    nonce: Uint256
    deadline: Seconds


class KeyProofMessage(ContractModel):
    action: Literal[3] = 3
    application_id: Hex32 = Field(alias="applicationId")
    issuer_id: Hex32 = Field(alias="issuerId")
    signer: Address
    challenge_nonce: Hex32 = Field(alias="challengeNonce")
    deadline: Seconds


class GovernanceProposal(ContractModel):
    action: Literal[1, 2, 3]
    issuer_id: Hex32 = Field(alias="issuerId")
    key_id: Hex32 = Field(alias="keyId")
    signer: Address
    metadata_hash: Hex32 = Field(alias="metadataHash")
    nonce: Uint256
    deadline: Seconds


class DocumentDraftRequest(ContractModel):
    request_id: RequestId
    doc_key: Hex32
    expected_version: Version
    expires_at: Seconds
    content: Content


class SigningRequest(ContractModel):
    signing_request_id: Annotated[str, Field(pattern=r"^wsr_[A-Za-z0-9_-]+$")]
    primary_type: Literal["Publish", "Revoke", "KeyProof"]
    domain: WalletDomain
    message: Annotated[
        PublishMessage | RevokeMessage | KeyProofMessage, Field(discriminator="action")
    ]
    expected_signer: Address
    original_base64: str | None = None
    content: Content | None = None

    @model_validator(mode="after")
    def consistent_type(self) -> Self:
        expected = {1: "Publish", 2: "Revoke", 3: "KeyProof"}[self.message.action]
        if self.primary_type != expected:
            raise ValueError("primary_type does not match message.action")
        if self.primary_type == "Publish" and (
            self.original_base64 is None or self.content is None
        ):
            raise ValueError("Publish requires original bytes and protected content")
        if isinstance(self.message, PublishMessage):
            from .wallet_signatures import original_bytes, validate_content

            validate_content(self.message, self.content)
            if base64.b64decode(self.original_base64, validate=True) != original_bytes(
                self.message, self.content
            ):
                raise ValueError("original_base64 differs from the agreed issuance bytes")
        if (
            isinstance(self.message, KeyProofMessage)
            and self.message.signer != self.expected_signer
        ):
            raise ValueError("key proof signer does not match expected_signer")
        return self


class SignedSubmission(ContractModel):
    request_id: RequestId
    signing_request_id: Annotated[str, Field(pattern=r"^wsr_[A-Za-z0-9_-]+$")]
    signature: Signature


class DirectTransaction(ContractModel):
    request_id: RequestId
    signing_request_id: Annotated[str, Field(pattern=r"^wsr_[A-Za-z0-9_-]+$")]
    tx_hash: Hex32


class ProposalRequest(ContractModel):
    request_id: RequestId
    proposal: GovernanceProposal
    key_proof_request_id: str | None = None


class ProposalView(ContractModel):
    proposal_id: Hex32
    proposal: GovernanceProposal
    status: Literal["PREPARED", "PENDING", "EXECUTED", "EXPIRED", "STALE"]
    approvals: list[Address]
    threshold: Literal[2] = 2
    operation_id: str | None = None
    key_proof: KeyProofMessage | None = None
    key_proof_signature: Signature | None = None


class KeyChallengeRequest(ContractModel):
    request_id: RequestId
    application_id: Annotated[str, Field(pattern=r"^app_[A-Za-z0-9_-]+$")]
    signer: Address


class KeyProofReceipt(ContractModel):
    signing_request_id: str
    verified_at: Seconds
    expires_at: Seconds


class RevokeDraftRequest(ContractModel):
    request_id: RequestId
    document_id: Hex32
    version: Version


class GovernanceTransaction(ContractModel):
    request_id: RequestId
    tx_hash: Hex32


class OperationView(ContractModel):
    operation_id: Annotated[str, Field(pattern=r"^op_[A-Za-z0-9_-]+$")]
    request_id: RequestId
    status: Literal["PENDING_SUBMISSION", "SUBMITTED", "CONFIRMED", "FAILED", "UNKNOWN"]
    tx_hash: Hex32 | None = None
    document_id: Hex32 | None = None
    version: Version | None = None
    recovery_required: bool
    next_action: Literal["WAIT", "RECONCILE", "RESIGN", "NONE"]


class DocumentView(ContractModel):
    document_id: Hex32
    issuer_id: Hex32
    doc_key: Hex32
    key_id: Hex32
    version: Version
    latest_version: Version
    state: Literal["ACTIVE", "REVOKED", "SUPERSEDED", "EXPIRED"]
    warnings: list[Literal["ISSUER_SUSPENDED", "KEY_COMPROMISED", "CHAIN_UNAVAILABLE"]]
    original_hash: Hex32
    protected_hash: Hex32
    content_schema: Hex32
    issued_at: Seconds
    expires_at: Seconds
    original_available: bool


class VerificationRequest(ContractModel):
    request_id: RequestId
    document_id: Hex32
    version: Version | None = None
    scope: Literal["ID_ONLY", "PROTECTED_FIELDS", "ORIGINAL_BYTES"]
    candidate: dict[str, str | int | None] | None = None
    original_ref: str | None = None

    @model_validator(mode="after")
    def scope_input(self) -> Self:
        if self.scope == "ID_ONLY" and (
            self.candidate is not None or self.original_ref is not None
        ):
            raise ValueError("ID_ONLY has no content comparison input")
        if self.scope == "PROTECTED_FIELDS" and (
            not self.candidate or self.original_ref is not None
        ):
            raise ValueError("PROTECTED_FIELDS requires only a nonempty candidate")
        if self.scope == "ORIGINAL_BYTES" and (not self.original_ref or self.candidate is not None):
            raise ValueError("ORIGINAL_BYTES requires only original_ref")
        return self


class CheckResult(ContractModel):
    name: str
    status: Literal["PASSED", "FAILED", "NOT_RUN", "UNAVAILABLE"]
    field_path: str | None = None
    reason_code: str | None = None


class VerificationResult(ContractModel):
    session_id: Annotated[str, Field(pattern=r"^vsn_[A-Za-z0-9_-]+$")]
    verification_status: Literal["VERIFIED", "NOT_REGISTERED", "TAMPERED", "INCONCLUSIVE", "ERROR"]
    comparison_scope: Literal["ID_ONLY", "FULL_COMPARISON", "PARTIAL_COMPARISON", "NONE"]
    document: DocumentView | None = None
    checks: list[CheckResult]
    reason_codes: list[str]
    checked_at: Seconds
    chain_id: Uint256
    verifying_contract: Address
    block_number: Uint256 | None = None
    block_hash: Hex32 | None = None

    @model_validator(mode="after")
    def verified_requires_evidence(self) -> Self:
        if self.verification_status == "VERIFIED":
            passed = {check.name for check in self.checks if check.status == "PASSED"}
            if (
                self.comparison_scope != "FULL_COMPARISON"
                or self.document is None
                or not {"signature", "current_state", "content"}.issubset(passed)
                or self.block_number is None
                or self.block_hash is None
            ):
                raise ValueError(
                    "VERIFIED requires full comparison, signature and current chain evidence"
                )
        return self


class AnalysisRequest(ContractModel):
    request_id: RequestId
    input_ref: str
    retain_report: bool = False
    retain_original: bool = False


class AnalysisEvidence(ContractModel):
    rule_id: str
    quote: Annotated[str, Field(max_length=500)]
    start_offset: Annotated[int, Field(strict=True, ge=0)] | None = None
    end_offset: Annotated[int, Field(strict=True, ge=0)] | None = None
    page: Annotated[int, Field(strict=True, ge=1)] | None = None
    start_ms: Annotated[int, Field(strict=True, ge=0)] | None = None
    end_ms: Annotated[int, Field(strict=True, ge=0)] | None = None
    source: Literal["RULE", "LLM"]

    @model_validator(mode="after")
    def valid_ranges(self) -> Self:
        for start, end in ((self.start_offset, self.end_offset), (self.start_ms, self.end_ms)):
            if (start is None) != (end is None) or (start is not None and start >= end):
                raise ValueError("evidence ranges must have both bounds and start < end")
        return self


class AnalysisReport(ContractModel):
    risk_level: Literal["HIGH", "CAUTION", "NO_CLEAR_INDICATORS", "UNDETERMINED"]
    evidence: list[AnalysisEvidence]
    limitations: list[str]
    verification: VerificationResult | None = None
    verification_not_run_reason: str | None = None

    @model_validator(mode="after")
    def explicit_verification_scope(self) -> Self:
        if self.verification is None and not self.verification_not_run_reason:
            raise ValueError("a missing issuance check requires verification_not_run_reason")
        if self.verification is not None and self.verification_not_run_reason is not None:
            raise ValueError("verification and verification_not_run_reason are mutually exclusive")
        return self


class AnalysisJob(ContractModel):
    analysis_id: Annotated[str, Field(pattern=r"^ana_[A-Za-z0-9_-]+$")]
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "EXPIRED"]
    retain_report: bool
    retain_original: bool
    result_expires_at: Seconds | None = None
    original_expires_at: Seconds | None = None
    report: AnalysisReport | None = None
    error_code: str | None = None


class AnalysisList(ContractModel):
    items: list[AnalysisJob]
    next_cursor: str | None = None


class ErrorResponse(ContractModel):
    detail: str
    request_id: RequestId | None = None
    retry_after_seconds: Annotated[int, Field(strict=True, ge=0)] | None = None
    field_paths: list[str] = Field(default_factory=list)


class DemoEmailRequest(ContractModel):
    email: Annotated[str, Field(min_length=3, max_length=254)]


class DemoEmailCode(ContractModel):
    code: Annotated[str, Field(pattern=r"^[0-9]{6}$")]


class OnboardingView(ContractModel):
    application_id: str
    roster_matched: bool
    demo_only: Literal[True] = True
    email_verified: bool
    internally_approved: bool
    metadata: dict
    metadata_hash: Hex32
    code_expires_at: Seconds | None = None


class DemoInbox(ContractModel):
    demo_only: Literal[True] = True
    code: str | None
    expires_at: Seconds


class TextInputRequest(ContractModel):
    kind: Literal["TEXT"]
    text: Annotated[str, Field(min_length=1, max_length=10000)]


class InputReceipt(ContractModel):
    input_ref: str
    expires_at: Seconds


class VerificationMaterial(ContractModel):
    signing_request: SigningRequest
    signature: Signature
    block_number: Uint256
    block_hash: Hex32
