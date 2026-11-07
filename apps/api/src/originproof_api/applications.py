from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .accounts import current_session, require_csrf
from .database import AccountRow, AuditEventRow, IssuerApplicationRow, SessionRow

router = APIRouter(tags=["issuer applications"])


class ApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issuer_name: str = Field(min_length=1, max_length=120)


class DecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVE", "REJECT"]
    reason: str = Field(min_length=1, max_length=500)


class ApplicationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    application_id: str
    issuer_id: str
    issuer_name: str
    applicant_account_id: str
    status: str
    decision_reason: str | None
    decided_by_account_id: str | None
    created_at: datetime


def _role(account: AccountRow, expected: str) -> None:
    if account.role != expected:
        raise HTTPException(403, "FORBIDDEN")


@router.post("/v1/issuer-applications", response_model=ApplicationView, status_code=201)
async def apply(
    body: ApplicationInput,
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> ApplicationView:
    account, session = identity
    _role(account, "issuer")
    require_csrf(request, session)
    if not account.issuer_id or not body.issuer_name.strip():
        raise HTTPException(422, "INVALID_ISSUER")
    row = IssuerApplicationRow(
        application_id=f"app_{uuid4().hex}",
        issuer_id=account.issuer_id,
        applicant_account_id=account.account_id,
        issuer_name=body.issuer_name.strip(),
        status="PENDING_REVIEW",
    )
    async with request.app.state.database.session_factory() as db:
        db.add(row)
        try:
            await db.commit()
        except IntegrityError as error:
            await db.rollback()
            raise HTTPException(409, "APPLICATION_EXISTS") from error
        await db.refresh(row)
        return ApplicationView.model_validate(row)


@router.get("/v1/issuer-applications/mine", response_model=ApplicationView | None)
async def my_application(
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> ApplicationView | None:
    account, _ = identity
    _role(account, "issuer")
    async with request.app.state.database.session_factory() as db:
        row = await db.scalar(
            select(IssuerApplicationRow).where(IssuerApplicationRow.issuer_id == account.issuer_id)
        )
        return ApplicationView.model_validate(row) if row else None


@router.get("/v1/operator/issuer-applications", response_model=list[ApplicationView])
async def applications(
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> list[ApplicationView]:
    account, _ = identity
    _role(account, "operator")
    async with request.app.state.database.session_factory() as db:
        rows = await db.scalars(
            select(IssuerApplicationRow).order_by(IssuerApplicationRow.created_at)
        )
        return [ApplicationView.model_validate(row) for row in rows]


@router.post(
    "/v1/operator/issuer-applications/{application_id}/decision",
    response_model=ApplicationView,
)
async def decide(
    application_id: str,
    body: DecisionInput,
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> ApplicationView:
    account, session = identity
    _role(account, "operator")
    require_csrf(request, session)
    if not body.reason.strip():
        raise HTTPException(422, "REASON_REQUIRED")
    async with request.app.state.database.session_factory() as db:
        row = await db.scalar(
            select(IssuerApplicationRow)
            .where(IssuerApplicationRow.application_id == application_id)
            .with_for_update()
        )
        if row is None:
            raise HTTPException(404, "APPLICATION_NOT_FOUND")
        if row.status != "PENDING_REVIEW":
            raise HTTPException(409, "ALREADY_DECIDED")
        if row.applicant_account_id == account.account_id:
            raise HTTPException(403, "SELF_APPROVAL_FORBIDDEN")
        previous = row.status
        row.status = "APPROVED_PENDING_CHAIN" if body.decision == "APPROVE" else "REJECTED"
        row.decision_reason = body.reason.strip()
        row.decided_by_account_id = account.account_id
        db.add(
            AuditEventRow(
                event_id=f"evt_{uuid4().hex}",
                actor_account_id=account.account_id,
                issuer_id=row.issuer_id,
                action="ISSUER_APPLICATION_DECISION",
                target_id=row.application_id,
                before_status=previous,
                after_status=row.status,
            )
        )
        await db.commit()
        await db.refresh(row)
        return ApplicationView.model_validate(row)
