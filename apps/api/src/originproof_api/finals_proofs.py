"""W3 issuance and read-only verification; Proof lifecycle/consume is a W4 dependency."""

import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from originproof_core import DependencyUnavailableError, payload_hash
from originproof_core.finals import (
    CheckState,
    FinalsProofType,
    FinalsReasonCode,
    FinalsSignedProofEnvelope,
    FinalsVerificationResult,
    OfficialDocument,
    PaymentRequest,
    VerificationScope,
    beneficiary_binding,
    recipient_binding,
    target_binding,
)
from originproof_core.finals_verification import evaluate_finals
from originproof_core.models import SignatureScheme, VerificationStatus
from originproof_core.signatures import signing_digest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import chain_management
from .accounts import COOKIE, current_session
from .database import (
    AccountRow,
    AuditEventRow,
    FinalsProofRow,
    IssuerKeyRow,
    RecipientTokenRow,
    SessionRow,
)
from .operations import input_fingerprint
from .signers import verify_signer

router = APIRouter(prefix="/v2", tags=["finals-proofs"])
Identity = Annotated[tuple[AccountRow, SessionRow], Depends(current_session)]


class PaymentIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proof_type: Literal["PAYMENT_REQUEST"]
    amount_minor: int = Field(gt=0, strict=True)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    target_ref: str = Field(min_length=1, max_length=500)

    @field_validator("target_ref")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("target reference required")
        return value


class DocumentIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proof_type: Literal["OFFICIAL_DOCUMENT"]
    institution_code: str = Field(min_length=1, max_length=120)
    document_type: str = Field(min_length=1, max_length=120)
    document_number: str = Field(min_length=1, max_length=120)
    version: int = Field(gt=0, strict=True)

    @field_validator("institution_code", "document_type", "document_number")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("document text must not be blank")
        return value


class IssueInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]{1,124}$")
    recipient_id: str = Field(min_length=1, max_length=64)
    expires_at: datetime
    content: Annotated[PaymentIssue | DocumentIssue, Field(discriminator="proof_type")]

    @field_validator("expires_at")
    @classmethod
    def whole_seconds(cls, value):
        if value.tzinfo is None or value.utcoffset() is None or value.microsecond:
            raise ValueError("timezone and whole seconds required")
        return value


class ProofView(BaseModel):
    proof_id: str
    issuer_id: str
    key_id: str
    proof_type: FinalsProofType
    schema_version: Literal["2.0.0"]
    issued_at: datetime
    expires_at: datetime
    verification_path: str


class ProofContent(BaseModel):
    envelope: FinalsSignedProofEnvelope
    target_ref: str | None = None


class RecipientView(BaseModel):
    recipient_id: str
    label: str


class ComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_minor: int | None = Field(default=None, gt=0, strict=True)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    target_ref: str | None = Field(default=None, min_length=1, max_length=500)
    institution_code: str | None = Field(default=None, min_length=1, max_length=120)
    document_type: str | None = Field(default=None, min_length=1, max_length=120)
    document_number: str | None = Field(default=None, min_length=1, max_length=120)
    version: int | None = Field(default=None, gt=0, strict=True)

    @model_validator(mode="after")
    def nonblank(self) -> Self:
        for value in (
            self.target_ref,
            self.institution_code,
            self.document_type,
            self.document_number,
        ):
            if value is not None and not value.strip():
                raise ValueError("comparison text must not be blank")
        return self


class VerifyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]{1,124}$")
    candidate: ComparisonInput | None = None


def view(row):
    envelope = FinalsSignedProofEnvelope.model_validate(row.envelope)
    return ProofView(
        **envelope.model_dump(
            include={
                "proof_id",
                "issuer_id",
                "key_id",
                "proof_type",
                "schema_version",
                "issued_at",
                "expires_at",
            }
        ),
        verification_path=f"/v2/proofs/{row.proof_id}",
    )


async def authorized_content(request, row, identity):
    account, _ = identity
    if account.role == "issuer" and account.issuer_id == row.issuer_id:
        return
    if account.role == "recipient" and account.account_id == row.recipient_account_id:
        async with request.app.state.database.session_factory() as db:
            token = await db.get(RecipientTokenRow, account.account_id)
        envelope = FinalsSignedProofEnvelope.model_validate(row.envelope)
        if (
            token
            and recipient_binding(row.proof_id, token.token, row.recipient_salt, envelope.chain_id)
            == envelope.subject_binding_hash
        ):
            return
    raise HTTPException(404, "PROOF_NOT_FOUND")


@router.get("/issuer/recipients", response_model=list[RecipientView])
async def recipients(request: Request, identity: Identity):
    account, _ = identity
    if account.role != "issuer" or not account.issuer_id:
        raise HTTPException(403, "FORBIDDEN")
    async with request.app.state.database.session_factory() as db:
        rows = await db.scalars(select(AccountRow).where(AccountRow.role == "recipient"))
        return [RecipientView(recipient_id=row.account_id, label=row.username) for row in rows]


@router.post("/issuer/proofs", response_model=ProofView)
async def issue(body: IssueInput, request: Request, identity: Identity):
    account = chain_management.authorize(request, identity, "issuer")
    manager = chain_management.service(request)
    fingerprint = input_fingerprint(body.model_dump(mode="json"))
    # Same durable P0 lock as key registration/revocation: issuance sees one selected key.
    async with chain_management.chain_lock(manager.database):
        async with manager.database.session_factory() as db:
            existing = await db.scalar(
                select(FinalsProofRow).where(
                    FinalsProofRow.account_id == account.account_id,
                    FinalsProofRow.request_id == body.request_id,
                )
            )
            if existing:
                if existing.input_hash != fingerprint or existing.issuer_id != account.issuer_id:
                    raise HTTPException(409, "REQUEST_ID_CONFLICT")
                return view(existing)
            settings = manager.settings
            allowed = {
                settings.finals_payment_issuer_id: "PAYMENT_REQUEST",
                settings.finals_document_issuer_id: "OFFICIAL_DOCUMENT",
            }
            if allowed.get(account.issuer_id) != body.content.proof_type:
                raise HTTPException(403, "PROOF_TYPE_FORBIDDEN")
            if isinstance(body.content, DocumentIssue) and (
                body.content.institution_code != settings.finals_document_institution_code
            ):
                raise HTTPException(422, "INSTITUTION_CODE_MISMATCH")
            recipient = await db.get(AccountRow, body.recipient_id)
            if recipient is None or recipient.role != "recipient":
                raise HTTPException(422, "INVALID_RECIPIENT")
            await manager.active_issuer(account.issuer_id)
            selected = list(
                await db.scalars(
                    select(IssuerKeyRow).where(
                        IssuerKeyRow.issuer_id == account.issuer_id,
                        IssuerKeyRow.selected.is_(True),
                    )
                )
            )
            if len(selected) != 1:
                raise HTTPException(409, "ISSUING_KEY_UNAVAILABLE")
            key = selected[0]
            try:
                public = await manager.key_view(key)
            except DependencyUnavailableError:
                raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
            if not public.selected or public.status != "ACTIVE":
                raise HTTPException(409, "ISSUING_KEY_UNAVAILABLE")
            # Check chain periods as well as the durable local key record.
            try:
                chain_key = await manager.reader(account.issuer_id).get_key(key.key_id)
            except DependencyUnavailableError:
                raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
            now = datetime.now(UTC).replace(microsecond=0)
            if body.expires_at <= now:
                raise HTTPException(422, "EXPIRY_IN_PAST")
            if (
                chain_key is None
                or chain_key.status != "ACTIVE"
                or chain_key.issuer_id != account.issuer_id
                or chain_key.signer.lower() != key.signer.lower()
                or not chain_key.valid_from <= now < chain_key.valid_until
            ):
                raise HTTPException(409, "ISSUING_KEY_UNAVAILABLE")
            try:
                signing_key = verify_signer(settings.signer_directory, key.secret_ref, key.signer)
            except (ValueError, OSError):
                raise HTTPException(409, "SIGNER_UNAVAILABLE") from None
            token = await db.get(RecipientTokenRow, recipient.account_id)
            if token is None:
                token = RecipientTokenRow(
                    account_id=recipient.account_id, token=secrets.token_hex(32)
                )
                db.add(token)
            proof_id, salt = f"prf_{uuid4().hex}", secrets.token_hex(32)
            binding = recipient_binding(proof_id, token.token, salt, manager.manifest.chain_id)
            content = body.content
            if isinstance(content, PaymentIssue):
                payload = PaymentRequest(
                    amount_minor=content.amount_minor,
                    currency=content.currency,
                    payer_binding=binding,
                    beneficiary_binding=beneficiary_binding(
                        account.issuer_id, manager.manifest.chain_id
                    ),
                    target_hash=target_binding(content.target_ref),
                )
            else:
                payload = OfficialDocument(
                    **content.model_dump(exclude={"proof_type"}), subject_token=binding
                )
            envelope = FinalsSignedProofEnvelope(
                proof_id=proof_id,
                issuer_id=account.issuer_id,
                key_id=key.key_id,
                proof_type=content.proof_type,
                schema_version="2.0.0",
                signature_scheme=SignatureScheme.ECDSA_SECP256K1_KECCAK256_V1,
                chain_id=manager.manifest.chain_id,
                app_domain="originproof.finals",
                payload=payload,
                payload_hash=payload_hash(payload),
                subject_binding_hash=binding,
                issued_at=now,
                expires_at=body.expires_at,
                nonce=secrets.token_hex(16),
                single_use=isinstance(content, PaymentIssue),
                signature="0x" + "00" * 65,
            )
            signature = signing_key.sign_msg_hash(bytes.fromhex(signing_digest(envelope)[2:]))
            envelope = envelope.model_copy(update={"signature": "0x" + signature.to_bytes().hex()})
            row = FinalsProofRow(
                proof_id=proof_id,
                account_id=account.account_id,
                issuer_id=account.issuer_id,
                key_id=key.key_id,
                request_id=body.request_id,
                input_hash=fingerprint,
                recipient_account_id=recipient.account_id,
                recipient_salt=salt,
                target_ref=content.target_ref if isinstance(content, PaymentIssue) else None,
                deployment_id=manager.manifest.deployment_id,
                envelope=envelope.model_dump(mode="json"),
            )
            db.add(row)
            db.add(
                AuditEventRow(
                    event_id=f"evt_{uuid4().hex}",
                    actor_account_id=account.account_id,
                    issuer_id=account.issuer_id,
                    action="issue_proof",
                    target_id=proof_id,
                    after_status="ISSUED",
                )
            )
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise HTTPException(409, "REQUEST_ID_CONFLICT") from None
            return view(row)


@router.get("/issuer/proofs", response_model=list[ProofView])
async def issuer_proofs(request: Request, identity: Identity):
    account, _ = identity
    if account.role != "issuer" or not account.issuer_id:
        raise HTTPException(403, "FORBIDDEN")
    async with request.app.state.database.session_factory() as db:
        rows = await db.scalars(
            select(FinalsProofRow)
            .where(FinalsProofRow.issuer_id == account.issuer_id)
            .order_by(FinalsProofRow.created_at.desc())
            .limit(100)
        )
        return [view(row) for row in rows]


async def proof_row(request, proof_id):
    async with request.app.state.database.session_factory() as db:
        row = await db.get(FinalsProofRow, proof_id)
    if row is None:
        raise HTTPException(404, "PROOF_NOT_FOUND")
    return row


@router.get("/proofs/{proof_id}", response_model=ProofView)
async def public_proof(proof_id: str, request: Request):
    return view(await proof_row(request, proof_id))


@router.get("/proofs/{proof_id}/content", response_model=ProofContent)
async def content(proof_id: str, request: Request, identity: Identity):
    row = await proof_row(request, proof_id)
    await authorized_content(request, row, identity)
    return ProofContent(envelope=row.envelope, target_ref=row.target_ref)


def unavailable_result(request_id, reason, *, missing=False):
    return FinalsVerificationResult(
        session_id=f"vsn_{uuid4().hex}",
        request_id=request_id,
        verified_at=datetime.now(UTC),
        verification_status=VerificationStatus.NOT_REGISTERED
        if missing
        else VerificationStatus.INCONCLUSIVE,
        lifecycle_status=None,
        scope=VerificationScope.PROOF_ONLY,
        reason_codes=[reason],
        checks=dict.fromkeys(
            (
                "contract",
                "payload_hash",
                "issuer",
                "issuer_key",
                "signature",
                "proof_status",
                "candidate_match",
            ),
            CheckState.NOT_RUN,
        ),
    )


async def optional_identity(request: Request):
    if not request.cookies.get(COOKIE):
        return None
    return await current_session(request)


@router.post("/proofs/{proof_id}/verify", response_model=FinalsVerificationResult)
async def verify(
    proof_id: str,
    body: VerifyInput,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow] | None, Depends(optional_identity)],
):
    try:
        row = await proof_row(request, proof_id)
    except HTTPException as error:
        if error.status_code != 404:
            raise
        return unavailable_result(body.request_id, FinalsReasonCode.PROOF_NOT_FOUND, missing=True)
    if body.candidate is not None:
        if identity is None:
            raise HTTPException(401, "AUTH_REQUIRED")
        await authorized_content(request, row, identity)
    try:
        envelope = FinalsSignedProofEnvelope.model_validate(row.envelope)
    except ValidationError:
        return unavailable_result(body.request_id, FinalsReasonCode.SCHEMA_UNSUPPORTED)
    candidate = None
    if body.candidate is not None:
        candidate = body.candidate.model_dump(exclude_none=True)
        if "target_ref" in candidate:
            candidate["target_hash"] = target_binding(candidate.pop("target_ref"))
    # Contract/hash failures precede RPC calls, as specified in ADR 0001.
    preliminary = evaluate_finals(
        envelope,
        request_id=body.request_id,
        chain_id=request.app.state.settings.blockchain_chain_id,
        issuer=None,
        key=None,
        candidate=candidate,
    )
    if preliminary.checks["contract"] == CheckState.FAIL or (
        preliminary.checks["payload_hash"] == CheckState.FAIL
    ):
        return preliminary
    try:
        manager = chain_management.service(request)
        if row.deployment_id != manager.manifest.deployment_id:
            raise DependencyUnavailableError("deployment changed")
        reader = manager.reader(row.issuer_id)
        issuer = await reader.get_issuer(row.issuer_id)
        key = await reader.get_key(row.key_id) if issuer is not None else None
    except (DependencyUnavailableError, HTTPException):
        result = unavailable_result(body.request_id, FinalsReasonCode.DEPENDENCY_UNAVAILABLE)
        result.checks.update(
            contract=CheckState.PASS, payload_hash=CheckState.PASS, issuer=CheckState.UNAVAILABLE
        )
        return result
    return evaluate_finals(
        envelope,
        request_id=body.request_id,
        chain_id=manager.manifest.chain_id,
        issuer=issuer,
        key=key,
        candidate=candidate,
    )
