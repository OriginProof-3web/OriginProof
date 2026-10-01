"""Authenticated W2 orchestration. B owns the EVM adapter."""

from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from infrastructure.blockchain import JsonRpcBlockchainReader, JsonRpcBlockchainWriter
from infrastructure.blockchain.manifest import load_manifest
from infrastructure.blockchain.writer import RpcRejected
from originproof_core import DependencyUnavailableError, IssuerTrustStatus, payload_hash
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text, update

from .accounts import current_session, require_csrf
from .database import (
    AccountRow,
    AuditEventRow,
    IssuerApplicationRow,
    IssuerKeyRow,
    OperationRow,
    SessionRow,
)
from .operations import OperationView, reserve_operation
from .signers import signer_key, verify_signer

router = APIRouter(tags=["issuer and key management"])


class MutationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(pattern=r"^req_[A-Za-z0-9_-]{1,124}$")
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def nonblank_reason(self):
        if not self.reason.strip():
            raise ValueError("reason required")
        return self


class KeyInput(MutationInput):
    valid_from: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def window(self):
        if any(t.tzinfo is None or t.microsecond for t in (self.valid_from, self.valid_until)):
            raise ValueError("timezone and whole seconds required")
        if not 0 <= self.valid_from.timestamp() < self.valid_until.timestamp() < 2**63:
            raise ValueError("invalid validity window")
        return self


class KeyStatus(StrEnum):
    PENDING_REGISTRATION = "PENDING_REGISTRATION"
    REGISTRATION_FAILED = "REGISTRATION_FAILED"
    ACTIVE = "ACTIVE"
    REVOCATION_PENDING = "REVOCATION_PENDING"
    REVOKED = "REVOKED"
    NOT_YET_VALID = "NOT_YET_VALID"
    EXPIRED = "EXPIRED"
    NOT_REGISTERED = "NOT_REGISTERED"
    DEPLOYMENT_CHANGED = "DEPLOYMENT_CHANGED"
    KEY_MISMATCH = "KEY_MISMATCH"
    SIGNER_UNAVAILABLE = "SIGNER_UNAVAILABLE"


class KeyView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key_id: str
    issuer_id: str
    signer: str
    valid_from: int
    valid_until: int
    status: KeyStatus
    selected: bool
    deployment_id: str


class IssuerView(BaseModel):
    issuer_id: str
    status: IssuerTrustStatus
    deployment_id: str
    chain_id: int


@asynccontextmanager
async def chain_lock(database):
    # ponytail: serialize local P0 writes across workers; per-sender locks if throughput matters.
    async with database.engine.connect() as connection:
        await connection.execute(text("SELECT pg_advisory_xact_lock(741031337)"))
        yield  # Connection rollback also releases the lock after cancellation.


class ChainManagement:
    def __init__(self, database, settings):
        self.database = database
        self.settings = settings
        if not settings.blockchain_rpc_url or not settings.blockchain_manifest_path:
            raise ValueError("chain unavailable")
        self.manifest = load_manifest(
            settings.blockchain_manifest_path, settings.blockchain_chain_id
        )
        self.writer = JsonRpcBlockchainWriter(
            settings.blockchain_rpc_url,
            settings.blockchain_manifest_path,
            expected_chain_id=settings.blockchain_chain_id,
        )

    def reader(self, issuer_id):
        return JsonRpcBlockchainReader(
            self.settings.blockchain_rpc_url,
            self.settings.blockchain_manifest_path,
            issuer_ids=[issuer_id],
            expected_chain_id=self.manifest.chain_id,
        )

    async def active_issuer(self, issuer_id):
        try:
            issuer = await self.reader(issuer_id).get_issuer(issuer_id)
        except DependencyUnavailableError:
            raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
        if issuer is None or issuer.status != "ACTIVE":
            raise HTTPException(409, "ISSUER_NOT_ACTIVE")
        return issuer

    async def key_view(self, row):
        if row.deployment_id != self.manifest.deployment_id:
            return KeyView.model_validate(row).model_copy(
                update={
                    "status": KeyStatus.DEPLOYMENT_CHANGED,
                    "selected": False,
                }
            )
        if row.status in ("PENDING_REGISTRATION", "REGISTRATION_FAILED"):
            return KeyView.model_validate(row)
        key = await self.reader(row.issuer_id).get_key(row.key_id)
        view = KeyView.model_validate(row)
        if key is None:
            return view.model_copy(update={"status": KeyStatus.NOT_REGISTERED, "selected": False})
        if key.issuer_id != row.issuer_id or key.signer.lower() != row.signer.lower():
            return view.model_copy(update={"status": KeyStatus.KEY_MISMATCH, "selected": False})
        now = int(datetime.now(UTC).timestamp())
        status = str(key.status)
        if status == "ACTIVE":
            if now < row.valid_from:
                status = "NOT_YET_VALID"
            elif now >= row.valid_until:
                status = "EXPIRED"
            elif row.status == "REVOCATION_PENDING":
                status = "REVOCATION_PENDING"
        selected = row.selected and status == "ACTIVE"
        if selected:
            try:
                verify_signer(self.settings.signer_directory, row.secret_ref, row.signer)
            except (ValueError, OSError):
                status, selected = "SIGNER_UNAVAILABLE", False
        return view.model_copy(update={"status": KeyStatus(status), "selected": selected})

    async def prepare(self, operation, nonce_override=None):
        body = operation.input_body
        nonce = (
            operation.recovery_reference.get("nonce")
            if operation.recovery_reference
            else nonce_override
        )
        roles = self.manifest.roles
        if operation.action == "register_issuer":
            async with self.database.session_factory() as db:
                application = await db.get(IssuerApplicationRow, operation.target_id)
                if application is None:
                    raise HTTPException(404, "APPLICATION_NOT_FOUND")
                metadata = payload_hash(
                    {"issuer_id": operation.issuer_id, "issuer_name": application.issuer_name}
                )
            prepared = await self.writer.prepare_register_issuer(
                roles["issuer_manager"],
                operation.issuer_id,
                roles["issuer_account"],
                metadata,
                nonce=nonce,
            )
        elif operation.action in ("suspend_issuer", "reactivate_issuer", "revoke_issuer"):
            prepared = await getattr(self.writer, "prepare_" + operation.action)(
                roles["issuer_manager"],
                operation.issuer_id,
                nonce=nonce,
            )
        elif operation.action == "register_key":
            key_id = "key_" + operation.operation_id.removeprefix("op_")
            async with self.database.session_factory() as db:
                row = await db.get(IssuerKeyRow, key_id)
                if row is None:
                    secret = signer_key(self.settings.signer_directory, key_id, create=True)
                    row = IssuerKeyRow(
                        key_id=key_id,
                        issuer_id=operation.issuer_id,
                        signer=secret.public_key.to_checksum_address(),
                        valid_from=int(datetime.fromisoformat(body["valid_from"]).timestamp()),
                        valid_until=int(datetime.fromisoformat(body["valid_until"]).timestamp()),
                        status="PENDING_REGISTRATION",
                        selected=False,
                        secret_ref=key_id,
                        deployment_id=self.manifest.deployment_id,
                    )
                    db.add(row)
                    await db.commit()
                if operation.target_id != key_id:
                    stored_operation = await db.get(OperationRow, operation.operation_id)
                    stored_operation.target_id = key_id
                    await db.commit()
                verify_signer(self.settings.signer_directory, row.secret_ref, row.signer)
                prepared = await self.writer.prepare_register_key(
                    roles["issuer_account"],
                    row.key_id,
                    row.issuer_id,
                    row.signer,
                    row.valid_from,
                    row.valid_until,
                    nonce=nonce,
                )
        elif operation.action == "revoke_key":
            prepared = await self.writer.prepare_revoke_key(
                roles["issuer_account"],
                operation.target_id,
                nonce=nonce,
            )
        else:
            raise ValueError("unsupported chain action")
        if not operation.recovery_reference and nonce_override is None:
            async with self.database.session_factory() as db:
                references = await db.scalars(
                    select(OperationRow.recovery_reference).where(
                        OperationRow.deployment_id == self.manifest.deployment_id,
                        OperationRow.status.in_(("PENDING_SUBMISSION", "SUBMITTED", "UNKNOWN")),
                        OperationRow.operation_id != operation.operation_id,
                    )
                )
                reserved = {
                    ref["nonce"]
                    for ref in references
                    if ref and ref["sender"].lower() == prepared.sender.lower()
                }
            if prepared.nonce in reserved:
                next_nonce = prepared.nonce
                while next_nonce in reserved:
                    next_nonce += 1
                return await self.prepare(operation, nonce_override=next_nonce)
        if operation.recovery_reference:
            prepared = self.writer.restore_prepared(prepared, operation.recovery_reference)
        return prepared

    async def run(self, operation):
        if operation.deployment_id and operation.deployment_id != self.manifest.deployment_id:
            raise HTTPException(409, "DEPLOYMENT_CHANGED")
        if operation.status in ("CONFIRMED", "FAILED"):
            return OperationView.model_validate(operation)
        try:
            prepared = await self.prepare(operation)
        except (ValueError, OSError, DependencyUnavailableError, httpx.HTTPError, RpcRejected):
            raise HTTPException(503, "CHAIN_OR_SIGNER_UNAVAILABLE") from None
        if operation.recovery_reference:
            result = await self.writer.recover_prepared(prepared, operation.tx_hash)
        else:
            result = await self.writer.execute_prepared(
                prepared, OperationPersistence(self.database, operation.operation_id)
            )
        async with self.database.session_factory() as db:
            row = await db.get(OperationRow, operation.operation_id)
            previous = row.status
            row.status = result.state.value
            row.tx_hash = result.tx_hash or row.tx_hash
            row.error_code = result.error_code
            row.deployment_id = result.deployment_id
            row.chain_evidence = {
                name: value
                for name, value in asdict(result).items()
                if name not in ("sender", "nonce", "recovery_id", "state")
            }
            if row.status == "CONFIRMED":
                await self.confirm_target(db, row)
            elif row.action == "register_key" and row.status == "FAILED":
                key = await db.get(IssuerKeyRow, "key_" + row.operation_id[3:])
                if key:
                    key.status = "REGISTRATION_FAILED"
            db.add(
                AuditEventRow(
                    event_id="evt_"
                    + row.operation_id[3:]
                    + "_"
                    + datetime.now(UTC).strftime("%H%M%S%f"),
                    actor_account_id=row.account_id,
                    issuer_id=row.issuer_id,
                    action=row.action,
                    reason=row.input_body.get("reason"),
                    target_id=row.target_id or row.operation_id,
                    before_status=previous,
                    after_status=row.status,
                )
            )
            await db.commit()
            await db.refresh(row)
            return OperationView.model_validate(row)

    async def confirm_target(self, db, row):
        if row.action == "register_issuer":
            application = await db.get(IssuerApplicationRow, row.target_id)
            application.status = "ACTIVE"
        elif row.action in ("suspend_issuer", "reactivate_issuer", "revoke_issuer"):
            application = await db.scalar(
                select(IssuerApplicationRow).where(IssuerApplicationRow.issuer_id == row.issuer_id)
            )
            application.status = {
                "suspend_issuer": "SUSPENDED",
                "reactivate_issuer": "ACTIVE",
                "revoke_issuer": "REVOKED",
            }[row.action]
        elif row.action == "register_key":
            key = await db.get(IssuerKeyRow, "key_" + row.operation_id[3:])
            await db.execute(
                update(IssuerKeyRow)
                .where(IssuerKeyRow.issuer_id == row.issuer_id)
                .values(selected=False)
            )
            key.status = "ACTIVE"
            key.selected = True
        elif row.action == "revoke_key":
            key = await db.get(IssuerKeyRow, row.target_id)
            key.status = "REVOKED"
            key.selected = False


class OperationPersistence:
    def __init__(self, database, operation_id):
        self.database, self.operation_id = database, operation_id

    async def save_prepared(self, reference):
        async with self.database.session_factory() as db:
            row = await db.get(OperationRow, self.operation_id)
            row.recovery_reference = reference
            row.deployment_id = reference["deployment_id"]
            await db.commit()

    async def save_submitted(self, recovery_id, tx_hash):
        async with self.database.session_factory() as db:
            row = await db.get(OperationRow, self.operation_id)
            if row.recovery_reference["recovery_id"] != recovery_id:
                raise ValueError("recovery mismatch")
            row.tx_hash = tx_hash
            row.status = "SUBMITTED"
            await db.commit()


def service(request):
    existing = getattr(request.app.state, "chain_management", None)
    if existing is not None:
        try:
            settings = request.app.state.settings
            current = load_manifest(settings.blockchain_manifest_path, settings.blockchain_chain_id)
            if current.deployment_id != existing.manifest.deployment_id:
                existing = None
        except (OSError, ValueError, KeyError):
            raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
    if existing is None:
        try:
            existing = ChainManagement(request.app.state.database, request.app.state.settings)
        except (OSError, ValueError, KeyError):
            raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
        request.app.state.chain_management = existing
    return existing


def authorize(request, identity, role):
    account, session = identity
    if account.role != role or (role == "issuer" and not account.issuer_id):
        raise HTTPException(403, "FORBIDDEN")
    require_csrf(request, session)
    return account


@router.post(
    "/v1/operator/issuer-applications/{application_id}/activate", response_model=OperationView
)
async def activate(
    application_id: str,
    body: MutationInput,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)],
):
    account = authorize(request, identity, "operator")
    manager = service(request)
    async with chain_lock(manager.database):
        async with manager.database.session_factory() as db:
            application = await db.get(IssuerApplicationRow, application_id)
            if application is None:
                raise HTTPException(404, "APPLICATION_NOT_FOUND")
            if application.applicant_account_id == account.account_id:
                raise HTTPException(403, "SELF_APPROVAL_FORBIDDEN")
            if application.status not in ("APPROVED_PENDING_CHAIN", "ACTIVE"):
                raise HTTPException(409, "APPLICATION_NOT_APPROVED")
            issuer_id = application.issuer_id
        operation = await reserve_operation(
            manager.database.session_factory,
            account,
            "register_issuer",
            body.request_id,
            body.model_dump(mode="json") | {"application_id": application_id},
            issuer_id=issuer_id,
            target_id=application_id,
        )
        return await manager.run(operation)


@router.post("/v1/operator/issuers/{issuer_id}/{action}", response_model=OperationView)
async def change_issuer(
    issuer_id: str,
    action: Literal["suspend", "reactivate", "revoke"],
    body: MutationInput,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)],
):
    account = authorize(request, identity, "operator")
    manager = service(request)
    async with chain_lock(manager.database):
        async with manager.database.session_factory() as db:
            application = await db.scalar(
                select(IssuerApplicationRow).where(IssuerApplicationRow.issuer_id == issuer_id)
            )
            if application is None:
                raise HTTPException(404, "ISSUER_NOT_FOUND")
            if application.applicant_account_id == account.account_id:
                raise HTTPException(403, "SELF_APPROVAL_FORBIDDEN")
            if application.status not in ("ACTIVE", "SUSPENDED", "REVOKED"):
                raise HTTPException(409, "ISSUER_NOT_REGISTERED")
        operation = await reserve_operation(
            manager.database.session_factory,
            account,
            action + "_issuer",
            body.request_id,
            body.model_dump(mode="json") | {"issuer_id": issuer_id},
            issuer_id=issuer_id,
            target_id=issuer_id,
        )
        return await manager.run(operation)


@router.get("/v1/issuer/status", response_model=IssuerView)
async def issuer_status(
    request: Request, identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)]
):
    account, _ = identity
    if account.role != "issuer" or not account.issuer_id:
        raise HTTPException(403, "FORBIDDEN")
    manager = service(request)
    try:
        issuer = await manager.reader(account.issuer_id).get_issuer(account.issuer_id)
    except DependencyUnavailableError:
        raise HTTPException(503, "CHAIN_UNAVAILABLE") from None
    if issuer is None:
        raise HTTPException(404, "ISSUER_NOT_FOUND")
    return IssuerView(
        issuer_id=account.issuer_id,
        status=issuer.status,
        deployment_id=manager.manifest.deployment_id,
        chain_id=manager.manifest.chain_id,
    )


@router.post("/v1/issuer/keys", response_model=OperationView)
async def register_key(
    body: KeyInput,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)],
):
    account = authorize(request, identity, "issuer")
    manager = service(request)
    async with chain_lock(manager.database):
        await manager.active_issuer(account.issuer_id)
        operation = await reserve_operation(
            manager.database.session_factory,
            account,
            "register_key",
            body.request_id,
            body.model_dump(mode="json"),
        )
        return await manager.run(operation)


@router.get("/v1/issuer/keys", response_model=list[KeyView])
async def list_keys(
    request: Request, identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)]
):
    account, _ = identity
    if account.role != "issuer" or not account.issuer_id:
        raise HTTPException(403, "FORBIDDEN")
    async with request.app.state.database.session_factory() as db:
        rows = await db.scalars(
            select(IssuerKeyRow).where(IssuerKeyRow.issuer_id == account.issuer_id)
        )
        rows = list(rows)
    try:
        manager = service(request)
        return [await manager.key_view(row) for row in rows]
    except DependencyUnavailableError:
        raise HTTPException(503, "CHAIN_UNAVAILABLE") from None


@router.get("/v1/issuer/keys/{key_id}", response_model=KeyView)
async def get_key(
    key_id: str,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)],
):
    account, _ = identity
    if account.role != "issuer" or not account.issuer_id:
        raise HTTPException(403, "FORBIDDEN")
    async with request.app.state.database.session_factory() as db:
        row = await db.get(IssuerKeyRow, key_id)
        if row is None or row.issuer_id != account.issuer_id:
            raise HTTPException(404, "KEY_NOT_FOUND")
    try:
        return await service(request).key_view(row)
    except DependencyUnavailableError:
        raise HTTPException(503, "CHAIN_UNAVAILABLE") from None


@router.post("/v1/issuer/keys/{key_id}/revoke", response_model=OperationView)
async def revoke_key(
    key_id: str,
    body: MutationInput,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)],
):
    account = authorize(request, identity, "issuer")
    manager = service(request)
    async with chain_lock(manager.database):
        async with manager.database.session_factory() as db:
            key = await db.get(IssuerKeyRow, key_id)
            if key is None or key.issuer_id != account.issuer_id:
                raise HTTPException(404, "KEY_NOT_FOUND")
            if key.deployment_id != manager.manifest.deployment_id:
                raise HTTPException(409, "DEPLOYMENT_CHANGED")
        operation = await reserve_operation(
            manager.database.session_factory,
            account,
            "revoke_key",
            body.request_id,
            body.model_dump(mode="json") | {"key_id": key_id},
            target_id=key_id,
        )
        if operation.status not in ("CONFIRMED", "FAILED"):
            async with manager.database.session_factory() as db:
                key = await db.get(IssuerKeyRow, key_id)
                # Disable issuance immediately, including uncertain chain revocation.
                key.selected = False
                key.status = "REVOKED" if key.status == "REVOKED" else "REVOCATION_PENDING"
                await db.commit()
        return await manager.run(operation)


@router.post("/v1/operations/{operation_id}/recover", response_model=OperationView)
async def recover(
    operation_id: str,
    request: Request,
    identity: Annotated[tuple[AccountRow, SessionRow], Depends(current_session)],
):
    account, session = identity
    require_csrf(request, session)
    manager = service(request)
    async with chain_lock(manager.database):
        async with manager.database.session_factory() as db:
            row = await db.get(OperationRow, operation_id)
            if row is None or (row.account_id != account.account_id and account.role != "operator"):
                raise HTTPException(404, "OPERATION_NOT_FOUND")
            if not row.recovery_reference and row.status not in ("CONFIRMED", "FAILED"):
                raise HTTPException(409, "NOT_SUBMITTED")
        return await manager.run(row)
