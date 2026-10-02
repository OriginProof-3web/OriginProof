"""Authenticated issuance and chain-backed lifecycle; reads never consume."""

import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from infrastructure.blockchain.reader import digest
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
from originproof_core.models import LifecycleStatus, SignatureScheme, VerificationStatus
from originproof_core.signatures import signing_digest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import chain_management
from .accounts import COOKIE, current_session, require_csrf
from .database import (
    AccountRow,
    AuditEventRow,
    FinalsProofRow,
    IssuerKeyRow,
    OperationRow,
    RecipientTokenRow,
    SessionRow,
)
from .operations import OperationStatus, OperationView, input_fingerprint, reserve_operation
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
    registration_status: OperationStatus | Literal["NOT_REGISTERED"] = "NOT_REGISTERED"
    registration_operation_id: str | None = None
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


async def view(row, request):
    async with request.app.state.database.session_factory() as db:
        operation = await db.scalar(
            select(OperationRow)
            .where(OperationRow.action == "register_proof", OperationRow.target_id == row.proof_id)
            .order_by(OperationRow.created_at.desc())
            .limit(1)
        )
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
        registration_status=operation.status if operation else "NOT_REGISTERED",
        registration_operation_id=operation.operation_id if operation else None,
        verification_path=f"/v2/proofs/{row.proof_id}",
    )


async def authorized_content(request, row, identity):
    account, _ = identity
    if account.role == "issuer" and account.issuer_id == row.issuer_id:
        return
    if account.role == "recipient" and account.account_id == row.recipient_account_id:
        async with request.app.state.database.session_factory() as db:
            token = await db.get(RecipientTokenRow, account.account_id)
        try:
            envelope = checked_envelope(row)
        except (ValidationError, ValueError):
            raise HTTPException(404, "PROOF_NOT_FOUND") from None
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
                await register_saved(manager, existing, account, body.request_id)
                return await view(existing, request)
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
            if key.status != "ACTIVE" or key.deployment_id != manager.manifest.deployment_id:
                raise HTTPException(409, "ISSUING_KEY_UNAVAILABLE")
            now = datetime.now(UTC).replace(microsecond=0)
            if body.expires_at <= now:
                raise HTTPException(422, "EXPIRY_IN_PAST")
            try:
                snapshot = await manager.reader(account.issuer_id).get_issuer_key_snapshot(
                    account.issuer_id, key.key_id, now
                )
            except DependencyUnavailableError:
                raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
            if snapshot.issuer is None or snapshot.issuer.status != "ACTIVE":
                raise HTTPException(409, "ISSUER_NOT_ACTIVE")
            chain_key = snapshot.key
            if (
                not snapshot.key_valid_at
                or chain_key is None
                or chain_key.signer.lower() != key.signer.lower()
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
        await register_saved(manager, row, account, body.request_id)
        return await view(row, request)


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
        return [await view(row, request) for row in rows]


async def proof_row(request, proof_id):
    async with request.app.state.database.session_factory() as db:
        row = await db.get(FinalsProofRow, proof_id)
    if row is None:
        raise HTTPException(404, "PROOF_NOT_FOUND")
    return row


@router.get("/proofs/{proof_id}", response_model=ProofView)
async def public_proof(proof_id: str, request: Request):
    return await view(await proof_row(request, proof_id), request)


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
        checked_envelope(row)
    except (ValidationError, ValueError):
        return unavailable_result(body.request_id, FinalsReasonCode.SCHEMA_UNSUPPORTED)
    candidate = None
    if body.candidate is not None:
        candidate = body.candidate.model_dump(exclude_none=True)
        if "target_ref" in candidate:
            candidate["target_hash"] = target_binding(candidate.pop("target_ref"))
    preliminary = evaluate_finals(
        checked_envelope(row),
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
    except HTTPException:
        return unavailable_result(body.request_id, FinalsReasonCode.DEPENDENCY_UNAVAILABLE)
    return await evaluate_saved(manager, row, body.request_id, candidate)


def checked_envelope(row):
    envelope = FinalsSignedProofEnvelope.model_validate(row.envelope)
    if (envelope.proof_id, envelope.issuer_id, envelope.key_id) != (
        row.proof_id,
        row.issuer_id,
        row.key_id,
    ):
        raise ValueError("stored proof identity mismatch")
    return envelope


async def evaluate_saved(manager, row, request_id, candidate=None, *, lifecycle=True):
    try:
        envelope = checked_envelope(row)
    except (ValidationError, ValueError):
        return unavailable_result(request_id, FinalsReasonCode.SCHEMA_UNSUPPORTED)
    preliminary = evaluate_finals(
        envelope,
        request_id=request_id,
        chain_id=manager.manifest.chain_id,
        issuer=None,
        key=None,
        candidate=candidate,
    )
    if preliminary.checks["contract"] == CheckState.FAIL or (
        preliminary.checks["payload_hash"] == CheckState.FAIL
    ):
        return preliminary
    try:
        if row.deployment_id != manager.manifest.deployment_id:
            raise DependencyUnavailableError("deployment changed")
        reader = manager.reader(row.issuer_id)
        snapshot = await reader.get_issuer_key_snapshot(
            row.issuer_id, row.key_id, envelope.issued_at
        )
    except DependencyUnavailableError:
        result = unavailable_result(request_id, FinalsReasonCode.DEPENDENCY_UNAVAILABLE)
        result.checks.update(
            contract=CheckState.PASS, payload_hash=CheckState.PASS, issuer=CheckState.UNAVAILABLE
        )
        return result
    now = datetime.now(UTC)
    result = evaluate_finals(
        envelope,
        request_id=request_id,
        chain_id=manager.manifest.chain_id,
        issuer=snapshot.issuer,
        key=snapshot.key,
        candidate=candidate,
        now=now,
    )
    if result.checks["signature"] != CheckState.PASS or not lifecycle:
        return result
    try:
        state = await reader.get_proof_state(row.proof_id, now)
        if state is None:
            return result.model_copy(
                update={
                    "verification_status": VerificationStatus.NOT_REGISTERED,
                    "lifecycle_status": None,
                    "reason_codes": [FinalsReasonCode.PROOF_NOT_FOUND],
                    "checks": result.checks | {"proof_status": CheckState.FAIL},
                }
            )
        if (state.deployment_id, state.chain_id, state.block_number, state.block_hash) != (
            snapshot.deployment_id,
            snapshot.chain_id,
            snapshot.block_number,
            snapshot.block_hash,
        ):
            raise DependencyUnavailableError("snapshot changed")
        if not matches_commitment(state, envelope):
            return result.model_copy(
                update={
                    "verification_status": VerificationStatus.INCONCLUSIVE,
                    "lifecycle_status": None,
                    "reason_codes": [FinalsReasonCode.CHAIN_COMMITMENT_MISMATCH],
                    "checks": result.checks | {"proof_status": CheckState.FAIL},
                }
            )
    except DependencyUnavailableError:
        return result.model_copy(
            update={
                "verification_status": VerificationStatus.INCONCLUSIVE,
                "lifecycle_status": None,
                "reason_codes": [FinalsReasonCode.DEPENDENCY_UNAVAILABLE],
                "checks": result.checks | {"proof_status": CheckState.UNAVAILABLE},
            }
        )
    async with manager.database.session_factory() as db:
        registration = await db.scalar(
            select(OperationRow)
            .where(
                OperationRow.action == "register_proof",
                OperationRow.target_id == row.proof_id,
                OperationRow.status == "CONFIRMED",
                OperationRow.deployment_id == manager.manifest.deployment_id,
            )
            .limit(1)
        )
    if registration is None:
        return result.model_copy(
            update={
                "verification_status": VerificationStatus.INCONCLUSIVE,
                "lifecycle_status": None,
                "reason_codes": [FinalsReasonCode.REGISTRATION_PENDING],
                "checks": result.checks | {"proof_status": CheckState.UNAVAILABLE},
            }
        )
    states = set()
    if state.revoked_at is not None:
        states.add(LifecycleStatus.PROOF_REVOKED)
    if state.consumed_at is not None:
        states.add(LifecycleStatus.CONSUMED)
    return evaluate_finals(
        envelope,
        request_id=request_id,
        chain_id=manager.manifest.chain_id,
        issuer=snapshot.issuer,
        key=snapshot.key,
        candidate=candidate,
        proof_states=states,
        now=now,
    )


def matches_commitment(state, envelope):
    return (
        state.proof_id == envelope.proof_id
        and state.issuer_id_hash == "0x" + digest(envelope.issuer_id).hex()
        and state.key_id_hash == "0x" + digest(envelope.key_id).hex()
        and state.signing_digest == signing_digest(envelope)
        and state.subject_binding_hash == envelope.subject_binding_hash
        and state.issued_at == envelope.issued_at
        and state.expires_at == envelope.expires_at
        and state.single_use == envelope.single_use
    )


class ProofMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]{1,124}$")


async def existing_operation(manager, account, action, body, row):
    async with manager.database.session_factory() as db:
        operation = await db.scalar(
            select(OperationRow).where(
                OperationRow.account_id == account.account_id,
                OperationRow.action == action,
                OperationRow.request_id == body["request_id"],
            )
        )
    if operation and (
        operation.input_hash != input_fingerprint(body) or operation.issuer_id != row.issuer_id
    ):
        raise HTTPException(409, "REQUEST_ID_CONFLICT")
    return operation


async def register_saved(manager, row, account, request_id):
    body = {"request_id": request_id, "proof_id": row.proof_id}
    existing = await existing_operation(manager, account, "register_proof", body, row)
    if existing:
        return await manager.run(existing)
    if row.deployment_id != manager.manifest.deployment_id:
        raise HTTPException(409, "DEPLOYMENT_CHANGED")
    # All requests for this immutable Proof share its original registration operation.
    async with manager.database.session_factory() as db:
        existing = await db.scalar(
            select(OperationRow)
            .where(OperationRow.action == "register_proof", OperationRow.target_id == row.proof_id)
            .order_by(OperationRow.created_at.desc())
            .limit(1)
        )
    if existing and existing.status != "FAILED":
        # Bind the new request ID to the same transaction, never allocate another nonce.
        if not existing.recovery_reference and existing.status != "CONFIRMED":
            raise HTTPException(409, "PROOF_REGISTRATION_PENDING")
        # Copy the recovery reference atomically with the alias reservation.
        # A crash must never leave an alias that can allocate a fresh transaction.
        alias = OperationRow(
            operation_id=f"op_{uuid4().hex}",
            account_id=account.account_id,
            issuer_id=row.issuer_id,
            action="register_proof",
            request_id=request_id,
            input_body=body,
            input_hash=input_fingerprint(body),
            target_id=row.proof_id,
            **{
                field: getattr(existing, field)
                for field in (
                    "status",
                    "tx_hash",
                    "error_code",
                    "deployment_id",
                    "recovery_reference",
                    "chain_evidence",
                )
            },
        )
        async with manager.database.session_factory() as db:
            db.add(alias)
            await db.commit()
            await db.refresh(alias)
        return await manager.run(alias)
    result = await evaluate_saved(manager, row, request_id, lifecycle=False)
    if FinalsReasonCode.DEPENDENCY_UNAVAILABLE in result.reason_codes:
        raise HTTPException(503, "CHAIN_UNAVAILABLE")
    if result.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(409, "PROOF_NOT_VERIFIED")
    if any(
        code in result.reason_codes
        for code in (
            FinalsReasonCode.ISSUER_SUSPENDED,
            FinalsReasonCode.ISSUER_KEY_REVOKED,
        )
    ):
        raise HTTPException(409, "PROOF_NOT_ACTIVE")
    envelope = checked_envelope(row)
    await require_binding(manager, row, envelope)
    operation = await reserve_operation(
        manager.database.session_factory,
        account,
        "register_proof",
        request_id,
        body,
        issuer_id=row.issuer_id,
        target_id=row.proof_id,
    )
    return await manager.run(operation)


@router.post("/issuer/proofs/{proof_id}/register", response_model=OperationView)
async def register(proof_id: str, body: ProofMutation, request: Request, identity: Identity):
    account = chain_management.authorize(request, identity, "issuer")
    manager = chain_management.service(request)
    async with chain_management.chain_lock(manager.database):
        row = await proof_row(request, proof_id)
        if row.issuer_id != account.issuer_id:
            raise HTTPException(404, "PROOF_NOT_FOUND")
        return await register_saved(manager, row, account, body.request_id)


@router.post("/issuer/proofs/{proof_id}/revoke", response_model=OperationView)
async def revoke(
    proof_id: str, body: chain_management.MutationInput, request: Request, identity: Identity
):
    account = chain_management.authorize(request, identity, "issuer")
    manager = chain_management.service(request)
    async with chain_management.chain_lock(manager.database):
        row = await proof_row(request, proof_id)
        if row.issuer_id != account.issuer_id:
            raise HTTPException(404, "PROOF_NOT_FOUND")
        inputs = body.model_dump(mode="json") | {"proof_id": proof_id}
        existing = await existing_operation(manager, account, "revoke_proof", inputs, row)
        if existing:
            return await manager.run(existing)
        result = await evaluate_saved(manager, row, body.request_id)
        if FinalsReasonCode.DEPENDENCY_UNAVAILABLE in result.reason_codes:
            raise HTTPException(503, "CHAIN_UNAVAILABLE")
        if result.verification_status != VerificationStatus.VERIFIED:
            raise HTTPException(409, "PROOF_NOT_VERIFIED")
        state = await mutation_state(manager, row)
        operation = await reserve_operation(
            manager.database.session_factory,
            account,
            "revoke_proof",
            body.request_id,
            inputs,
            issuer_id=row.issuer_id,
            target_id=proof_id,
        )
        if state.revoked_at is not None:
            # Observe the canonical state without another transaction or event.
            async with manager.database.session_factory() as db:
                stored = await db.get(OperationRow, operation.operation_id)
                stored.status = "CONFIRMED"
                stored.deployment_id = state.deployment_id
                stored.chain_evidence = {
                    "no_change": True,
                    "block_number": state.block_number,
                    "block_hash": state.block_hash,
                    "consumed_at": state.consumed_at.isoformat() if state.consumed_at else None,
                }
                db.add(
                    AuditEventRow(
                        event_id=f"evt_{uuid4().hex}",
                        actor_account_id=account.account_id,
                        issuer_id=row.issuer_id,
                        action="revoke_proof",
                        target_id=proof_id,
                        reason=body.reason,
                        before_status="REVOKED",
                        after_status="REVOKED",
                    )
                )
                await db.commit()
                await db.refresh(stored)
                return OperationView.model_validate(stored)
        return await manager.run(operation)


async def mutation_state(manager, row):
    if row.deployment_id != manager.manifest.deployment_id:
        raise HTTPException(409, "DEPLOYMENT_CHANGED")
    try:
        envelope = checked_envelope(row)
        state = await manager.reader(row.issuer_id).get_proof_state(row.proof_id, datetime.now(UTC))
    except (ValueError, ValidationError):
        raise HTTPException(409, "INVALID_STORED_PROOF") from None
    except DependencyUnavailableError:
        raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
    if state is None:
        raise HTTPException(409, "PROOF_NOT_REGISTERED")
    if not matches_commitment(state, envelope):
        raise HTTPException(409, "CHAIN_COMMITMENT_MISMATCH")
    return state


@router.post("/proofs/{proof_id}/consume", response_model=OperationView)
async def consume(proof_id: str, body: ProofMutation, request: Request, identity: Identity):
    account, session = identity
    require_csrf(request, session)
    manager = chain_management.service(request)
    async with chain_management.chain_lock(manager.database):
        row = await proof_row(request, proof_id)
        await authorized_content(request, row, identity)
        try:
            envelope = checked_envelope(row)
        except (ValidationError, ValueError):
            raise HTTPException(409, "INVALID_STORED_PROOF") from None
        inputs = body.model_dump(mode="json") | {
            "proof_id": proof_id,
            "actor_kind": 0 if account.role == "issuer" else 1,
            "actor_binding": "0x" + digest(row.issuer_id).hex()
            if account.role == "issuer"
            else envelope.subject_binding_hash,
        }
        existing = await existing_operation(manager, account, "consume_proof", inputs, row)
        if existing:
            return await manager.run(existing)
        async with manager.database.session_factory() as db:
            pending = await db.scalar(
                select(OperationRow.operation_id)
                .where(
                    OperationRow.action == "consume_proof",
                    OperationRow.target_id == proof_id,
                    OperationRow.status.in_(("PENDING_SUBMISSION", "SUBMITTED", "UNKNOWN")),
                )
                .limit(1)
            )
        if pending:
            raise HTTPException(409, "PROOF_OPERATION_PENDING")
        result = await evaluate_saved(manager, row, body.request_id)
        if FinalsReasonCode.DEPENDENCY_UNAVAILABLE in result.reason_codes:
            raise HTTPException(503, "CHAIN_UNAVAILABLE")
        if result.verification_status != VerificationStatus.VERIFIED:
            raise HTTPException(409, "PROOF_NOT_VERIFIED")
        if FinalsReasonCode.REPLAY_DETECTED in result.reason_codes:
            raise HTTPException(409, "REPLAY_DETECTED")
        if result.lifecycle_status != LifecycleStatus.ACTIVE:
            raise HTTPException(409, "PROOF_NOT_ACTIVE")
        envelope = checked_envelope(row)
        if not envelope.single_use:
            raise HTTPException(409, "PROOF_NOT_SINGLE_USE")
        state = await mutation_state(manager, row)
        if not state.consumable_at:
            raise HTTPException(409, "PROOF_NOT_CONSUMABLE")
        await require_binding(manager, row, envelope)
        operation = await reserve_operation(
            manager.database.session_factory,
            account,
            "consume_proof",
            body.request_id,
            inputs,
            issuer_id=row.issuer_id,
            target_id=proof_id,
        )
        return await manager.run(operation)


async def require_binding(manager, row, envelope):
    async with manager.database.session_factory() as db:
        token = await db.get(RecipientTokenRow, row.recipient_account_id)
    if (
        token is None
        or recipient_binding(row.proof_id, token.token, row.recipient_salt, envelope.chain_id)
        != envelope.subject_binding_hash
    ):
        raise HTTPException(409, "SUBJECT_BINDING_MISMATCH")


class ProofReconciliation(BaseModel):
    proof_id: str
    database_registration_status: str
    deployment_matches: bool
    registration_consistent: bool | None
    current_verification: FinalsVerificationResult
    authority: str = "CANONICAL_READER"


@router.get("/issuer/proofs/{proof_id}/reconciliation", response_model=ProofReconciliation)
async def reconcile(proof_id: str, request: Request, identity: Identity):
    account, _ = identity
    if account.role not in ("operator", "issuer"):
        raise HTTPException(403, "FORBIDDEN")
    row = await proof_row(request, proof_id)
    if account.role != "operator" and account.issuer_id != row.issuer_id:
        raise HTTPException(404, "PROOF_NOT_FOUND")
    manager = chain_management.service(request)
    stored = await view(row, request)
    current = await evaluate_saved(manager, row, f"req_reconcile_{uuid4().hex}")
    deployment_matches = row.deployment_id == manager.manifest.deployment_id
    consistent = None
    if deployment_matches and current.verification_status != VerificationStatus.INCONCLUSIVE:
        chain_registered = current.verification_status == VerificationStatus.VERIFIED
        if stored.registration_status == "CONFIRMED":
            consistent = chain_registered
        elif stored.registration_status in ("FAILED", "NOT_REGISTERED"):
            consistent = not chain_registered
    return ProofReconciliation(
        proof_id=proof_id,
        database_registration_status=stored.registration_status,
        deployment_matches=deployment_matches,
        registration_consistent=consistent,
        current_verification=current,
    )
