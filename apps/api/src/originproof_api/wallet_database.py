"""Additive wallet storage; legacy keys, Proofs and Operations retain their meaning."""

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class WalletOnboardingRow(Base):
    __tablename__ = "wallet_onboarding"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("issuer_applications.application_id"), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(254))
    code_hash: Mapped[str | None] = mapped_column(String(128))
    demo_code: Mapped[str | None] = mapped_column(String(6))
    code_expires_at: Mapped[int] = mapped_column(BigInteger, default=0)
    issued_at: Mapped[int] = mapped_column(BigInteger, default=0)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    failures: Mapped[list] = mapped_column(JSON, default=list)
    code_failures: Mapped[int] = mapped_column(default=0)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    internally_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("accounts.account_id"))
    metadata_value: Mapped[dict] = mapped_column(JSON)


class WalletSigningRow(Base):
    __tablename__ = "wallet_signing_requests"
    __table_args__ = (UniqueConstraint("account_id", "kind", "request_id"),)
    signing_request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"))
    issuer_id: Mapped[str] = mapped_column(String(66))
    kind: Mapped[str] = mapped_column(String(16))
    request_id: Mapped[str] = mapped_column(String(128))
    input_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str | None] = mapped_column(String(132))
    verified_request_id: Mapped[str | None] = mapped_column(String(128))
    verified_at: Mapped[int | None] = mapped_column(BigInteger)
    consumed_by: Mapped[str | None] = mapped_column(String(66))
    expires_at: Mapped[int] = mapped_column(BigInteger)


class WalletProposalRow(Base):
    __tablename__ = "wallet_proposals"
    __table_args__ = (UniqueConstraint("account_id", "request_id"),)
    proposal_id: Mapped[str] = mapped_column(String(66), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"))
    request_id: Mapped[str] = mapped_column(String(128))
    input_hash: Mapped[str] = mapped_column(String(64))
    domain: Mapped[dict] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON)


class WalletDocumentRow(Base):
    __tablename__ = "wallet_document_versions"
    chain_id: Mapped[str] = mapped_column(String(78), primary_key=True)
    verifying_contract: Mapped[str] = mapped_column(String(42), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(66), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signing_request_id: Mapped[str] = mapped_column(
        ForeignKey("wallet_signing_requests.signing_request_id"), unique=True
    )
    issuer_id: Mapped[str] = mapped_column(String(66))
    message: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)
    original: Mapped[bytes | None] = mapped_column(LargeBinary)
    signature: Mapped[str | None] = mapped_column(String(132))
    retain_until: Mapped[int] = mapped_column(BigInteger)


class WalletInputRow(Base):
    __tablename__ = "wallet_inputs"
    input_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    original: Mapped[bytes | None] = mapped_column(LargeBinary)
    accepted_at: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[int] = mapped_column(BigInteger)


class WalletAnalysisRow(Base):
    __tablename__ = "wallet_analyses"
    __table_args__ = (UniqueConstraint("account_id", "request_id"),)
    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    input_id: Mapped[str] = mapped_column(ForeignKey("wallet_inputs.input_id"), unique=True)
    request_id: Mapped[str] = mapped_column(String(128))
    input_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    accepted_at: Mapped[int] = mapped_column(BigInteger)
    started_at: Mapped[int | None] = mapped_column(BigInteger)
    completed_at: Mapped[int | None] = mapped_column(BigInteger)
    retain_report: Mapped[bool] = mapped_column(Boolean)
    retain_original: Mapped[bool] = mapped_column(Boolean)
    report_expires_at: Mapped[int | None] = mapped_column(BigInteger)
    original_expires_at: Mapped[int | None] = mapped_column(BigInteger)
    report: Mapped[dict | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(64))
