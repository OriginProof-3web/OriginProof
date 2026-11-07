from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, computed_field
from sqlalchemy import BigInteger, and_, cast, or_, select
from sqlalchemy.exc import IntegrityError

from .accounts import current_session
from .database import AccountRow, AuditEventRow, OperationRow, SessionRow

router = APIRouter(tags=["operations"])
WALLET_OPERATION_RETENTION = 30 * 86400


def expired_wallet_operations(stamp):
    resolved = cast(OperationRow.recovery_reference["resolved_at"].as_string(), BigInteger)
    return and_(
        OperationRow.action.startswith("wallet_", autoescape=True),
        OperationRow.status.in_(("CONFIRMED", "FAILED")),
        resolved.is_not(None),
        resolved <= stamp - WALLET_OPERATION_RETENTION,
    )


def require_retained_operation(row, stamp):
    resolved = (row.recovery_reference or {}).get("resolved_at")
    if (
        row.action.startswith("wallet_")
        and row.status in ("CONFIRMED", "FAILED")
        and resolved is not None
        and stamp >= int(resolved) + WALLET_OPERATION_RETENTION
    ):
        raise HTTPException(410, "RESULT_EXPIRED")


def expired_wallet_audits(stamp):
    protected = (
        select(OperationRow.operation_id)
        .where(
            OperationRow.action.startswith("wallet_", autoescape=True),
            ~expired_wallet_operations(stamp),
            or_(
                OperationRow.target_id == AuditEventRow.target_id,
                OperationRow.operation_id == AuditEventRow.target_id,
            ),
        )
        .exists()
    )
    return and_(
        AuditEventRow.action.startswith("wallet_", autoescape=True),
        AuditEventRow.created_at
        <= datetime.fromtimestamp(stamp, UTC) - timedelta(seconds=WALLET_OPERATION_RETENTION),
        ~protected,
    )


class OperationStatus(StrEnum):
    PENDING_SUBMISSION = "PENDING_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class OperationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    operation_id: str
    issuer_id: str | None
    target_id: str | None = None
    action: str
    request_id: str
    status: OperationStatus
    deployment_id: str | None = None
    chain_evidence: dict | None = None
    tx_hash: str | None
    error_code: str | None
    created_at: datetime

    @computed_field
    @property
    def recovery_required(self) -> bool:
        return self.status in (OperationStatus.UNKNOWN, OperationStatus.SUBMITTED) or (
            self.action.startswith("wallet_") and self.status == OperationStatus.PENDING_SUBMISSION
        )

    @computed_field
    @property
    def next_action(self) -> str:
        if self.action.startswith("wallet_"):
            if self.error_code == "SIGNATURE_EXPIRED":
                return "RESIGN"
            return "RECONCILE" if self.recovery_required else "NONE"
        if self.recovery_required:
            return "RECOVER_SAME_OPERATION"
        if self.status == OperationStatus.PENDING_SUBMISSION:
            return "RETRY_SAME_REQUEST"
        return "NONE"


class AuditView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: str
    actor_account_id: str
    issuer_id: str | None
    action: str
    target_id: str
    reason: str | None = None
    before_status: str | None
    after_status: str
    created_at: datetime


def input_fingerprint(body: dict[str, object]) -> str:
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


async def reserve_operation(
    session_factory,
    account: AccountRow,
    action: str,
    request_id: str,
    body: dict[str, object],
    *,
    issuer_id: str | None = None,
    target_id: str | None = None,
) -> OperationRow:
    """Commit a reservation before any external write; ambiguous submission stays pending."""
    if not re.fullmatch(r"req_[A-Za-z0-9_-]{1,124}", request_id):
        raise HTTPException(422, "INVALID_REQUEST_ID")
    fingerprint = input_fingerprint(body)
    institution = issuer_id if issuer_id is not None else account.issuer_id
    async with session_factory() as db:
        row = OperationRow(
            operation_id=f"op_{uuid4().hex}",
            account_id=account.account_id,
            issuer_id=institution,
            input_body=body,
            target_id=target_id,
            action=action,
            request_id=request_id,
            input_hash=fingerprint,
            status="PENDING_SUBMISSION",
        )
        db.add(row)
        db.add(
            AuditEventRow(
                event_id=f"evt_{uuid4().hex}",
                actor_account_id=account.account_id,
                issuer_id=institution,
                action=action,
                target_id=target_id or row.operation_id,
                reason=body.get("reason"),
                before_status=None,
                after_status="PENDING_SUBMISSION",
            )
        )
        try:
            await db.commit()
            await db.refresh(row)
            return row
        except IntegrityError as error:
            await db.rollback()
            existing = await db.scalar(
                select(OperationRow).where(
                    OperationRow.account_id == account.account_id,
                    OperationRow.action == action,
                    OperationRow.request_id == request_id,
                )
            )
            if existing is None:
                raise
            if existing.input_hash != fingerprint or existing.issuer_id != institution:
                raise HTTPException(409, "REQUEST_ID_CONFLICT") from error
            return existing


@router.get("/v1/operations/{operation_id}", response_model=OperationView)
async def operation(
    operation_id: str,
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> OperationView:
    account, _ = identity
    async with request.app.state.database.session_factory() as db:
        row = await db.get(OperationRow, operation_id)
        if row is None:
            raise HTTPException(404, "OPERATION_NOT_FOUND")
        same_institution = (
            account.role == "issuer"
            and account.issuer_id is not None
            and row.issuer_id == account.issuer_id
        )
        if (
            account.role != "operator"
            and row.account_id != account.account_id
            and not same_institution
        ):
            raise HTTPException(404, "OPERATION_NOT_FOUND")
        require_retained_operation(row, int(time.time()))
        return OperationView.model_validate(row)


@router.get("/v1/audit-events", response_model=list[AuditView])
async def audit_events(
    request: Request,
    target_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> list[AuditView]:
    account, _ = identity
    if account.role not in ("operator", "issuer"):
        raise HTTPException(403, "FORBIDDEN")
    if account.role == "issuer" and not account.issuer_id:
        raise HTTPException(403, "FORBIDDEN")
    query = (
        select(AuditEventRow)
        .where(~expired_wallet_audits(int(time.time())))
        .order_by(AuditEventRow.created_at, AuditEventRow.event_id)
    )
    if target_id is not None:
        query = query.where(AuditEventRow.target_id == target_id)
    query = query.limit(limit).offset(offset)
    if account.role == "issuer":
        query = query.where(AuditEventRow.issuer_id == account.issuer_id)
    async with request.app.state.database.session_factory() as db:
        rows = await db.scalars(query)
        return [AuditView.model_validate(row) for row in rows]


@router.get("/v1/operations", response_model=list[OperationView])
async def operation_list(
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
    target_id: str | None = Query(default=None, max_length=128),
    status: OperationStatus | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[OperationView]:
    account, _ = identity
    query = (
        select(OperationRow)
        .where(~expired_wallet_operations(int(time.time())))
        .order_by(OperationRow.created_at, OperationRow.operation_id)
    )
    if account.role != "operator":
        allowed = OperationRow.account_id == account.account_id
        if account.role == "issuer" and account.issuer_id:
            allowed = or_(allowed, OperationRow.issuer_id == account.issuer_id)
        query = query.where(allowed)
    if target_id is not None:
        query = query.where(OperationRow.target_id == target_id)
    if status is not None:
        query = query.where(OperationRow.status == status.value)
    async with request.app.state.database.session_factory() as db:
        rows = await db.scalars(query.limit(limit).offset(offset))
        return [OperationView.model_validate(row) for row in rows]
