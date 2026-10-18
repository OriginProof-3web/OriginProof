"""Synthetic roster/email/internal approval, separate from on-chain governance."""

import asyncio
import hmac
import re
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import (
    DemoEmailCode,
    DemoEmailRequest,
    DemoInbox,
    OnboardingView,
)
from sqlalchemy import select, update

from .accounts import current_session
from .applications import DecisionInput
from .database import IssuerApplicationRow
from .wallet_database import WalletOnboardingRow
from .wallet_runtime import now, runtime, sha256

router = APIRouter(prefix="/v3/issuer-applications", tags=["wallet onboarding"])
Identity = Annotated[tuple, Depends(current_session)]
ROSTER = {
    "iss_origin_mock_bank": ("Origin Mock Bank", "bank.example.invalid"),
    "iss_origin_mock_office": ("Origin Mock Office", "office.example.invalid"),
}


def code_verifier(settings, row, salt, code):
    secret = settings.wallet_email_secret
    if secret is None or len(secret.get_secret_value().encode()) < 32:
        raise HTTPException(503, "DEMO_EMAIL_SECRET_NOT_CONFIGURED")
    message = canonical_json_bytes([row.application_id, row.email, salt, code])
    digest = hmac.digest(secret.get_secret_value().encode(), message, "sha256").hex()
    return f"hmac-sha256:{salt}:{digest}"


async def expire_codes(app):
    service = app.state.wallet_runtime
    async with service.database.session_factory() as db:
        await db.execute(
            update(WalletOnboardingRow)
            .where(
                WalletOnboardingRow.code_expires_at <= now(),
                WalletOnboardingRow.code_hash.is_not(None)
                | WalletOnboardingRow.demo_code.is_not(None),
            )
            .values(code_hash=None, demo_code=None)
        )
        await service.commit(db)


async def maintain_email_codes(app, stop):
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=300)
        except TimeoutError:
            try:
                await expire_codes(app)
                app.state.wallet_email_cleanup_error = None
            except Exception:
                app.state.wallet_email_cleanup_error = "EMAIL_CLEANUP_UNAVAILABLE"


async def application(db, application_id, account, *, owner=True):
    row = await db.scalar(
        select(IssuerApplicationRow)
        .where(IssuerApplicationRow.application_id == application_id)
        .with_for_update()
    )
    if (
        row is None
        or row.issuer_id != account.issuer_id
        or (owner and row.applicant_account_id != account.account_id)
    ):
        raise HTTPException(404, "APPLICATION_NOT_FOUND")
    entry = ROSTER.get(row.issuer_id)
    if not entry or row.issuer_name != entry[0]:
        raise HTTPException(409, "SYNTHETIC_ROSTER_MISMATCH")
    return row, entry


def view(row):
    return OnboardingView(
        application_id=row.application_id,
        roster_matched=True,
        email_verified=row.email_verified,
        internally_approved=row.internally_approved,
        metadata=row.metadata_value,
        metadata_hash=sha256(canonical_json_bytes(row.metadata_value)),
        code_expires_at=row.code_expires_at or None,
    )


@router.get("/{application_id}", response_model=OnboardingView)
async def onboarding_status(application_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer", mutation=False)
    async with service.database.session_factory() as db:
        await application(db, application_id, account)
        row = await db.get(WalletOnboardingRow, application_id)
        if row is None:
            raise HTTPException(404, "ONBOARDING_NOT_STARTED")
        return view(row)


@router.post("/{application_id}/email-codes", response_model=OnboardingView, status_code=201)
async def issue_code(
    application_id: str, body: DemoEmailRequest, request: Request, identity: Identity
):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    if not service.settings.wallet_demo_email_enabled:
        raise HTTPException(503, "DEMO_EMAIL_NOT_ENABLED")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        app, entry = await application(db, application_id, account)
        email = body.email.strip().lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@" + re.escape(entry[1]), email):
            raise HTTPException(422, "DEMO_EMAIL_DOMAIN_MISMATCH")
        row = await db.get(WalletOnboardingRow, application_id)
        stamp = now()
        if row is None:
            row = WalletOnboardingRow(
                application_id=application_id,
                email=email,
                issues=[],
                failures=[],
                issued_at=0,
                email_verified=False,
                internally_approved=False,
                metadata_value={
                    "issuer_id": service.issuer_id(account),
                    "name": entry[0],
                    "domain": entry[1],
                },
            )
            db.add(row)
        if row.issued_at and stamp < row.issued_at + 60:
            raise HTTPException(429, "EMAIL_REISSUE_LIMIT", headers={"Retry-After": "60"})
        issues = [t for t in row.issues if t > stamp - 600]
        if len(issues) >= 3:
            raise HTTPException(429, "EMAIL_ISSUE_LIMIT", headers={"Retry-After": "600"})
        if len([t for t in row.failures if t > stamp - 900]) >= 10:
            raise HTTPException(429, "EMAIL_ATTEMPT_LIMIT", headers={"Retry-After": "900"})
        code, salt = f"{secrets.randbelow(1_000_000):06d}", secrets.token_hex(16)
        row.email = email
        row.code_hash = code_verifier(service.settings, row, salt, code)
        row.demo_code = code
        row.code_expires_at, row.issued_at = stamp + 300, stamp
        row.issues, row.code_failures = issues + [stamp], 0
        row.email_verified, row.internally_approved, row.approved_by = False, False, None
        service.audit(db, account, "wallet_email_issued", app.application_id, "PENDING")
        await service.commit(db)
        return view(row)


@router.get("/{application_id}/demo-inbox", response_model=DemoInbox)
async def demo_inbox(application_id: str, request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer", mutation=False)
    if not service.settings.wallet_demo_email_enabled:
        raise HTTPException(404, "NOT_FOUND")
    async with service.database.session_factory() as db:
        await application(db, application_id, account)
        row = await db.get(WalletOnboardingRow, application_id)
        if row is None:
            raise HTTPException(404, "NOT_FOUND")
        if now() >= row.code_expires_at and (row.demo_code or row.code_hash):
            row.code_hash, row.demo_code = None, None
            await service.commit(db)
        return DemoInbox(
            code=row.demo_code if now() < row.code_expires_at else None,
            expires_at=row.code_expires_at,
        )


@router.post("/{application_id}/email-verifications", response_model=OnboardingView)
async def verify_code(
    application_id: str, body: DemoEmailCode, request: Request, identity: Identity
):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    async with service.database.session_factory() as db:
        await service.lock_account(db, account)
        await application(db, application_id, account)
        row = await db.get(WalletOnboardingRow, application_id)
        stamp = now()
        if row is None:
            raise HTTPException(410, "EMAIL_CODE_EXPIRED")
        if stamp >= row.code_expires_at:
            row.code_hash, row.demo_code = None, None
            await service.commit(db)
            raise HTTPException(410, "EMAIL_CODE_EXPIRED")
        failures = [t for t in row.failures if t > stamp - 900]
        if row.code_failures >= 5 or len(failures) >= 10:
            raise HTTPException(429, "EMAIL_ATTEMPT_LIMIT", headers={"Retry-After": "900"})
        if row.code_hash is None:
            raise HTTPException(410, "EMAIL_CODE_EXPIRED")
        match = re.fullmatch(r"hmac-sha256:([a-f0-9]{32}):[a-f0-9]{64}", row.code_hash)
        if match is None:
            # Pre-HMAC codes cannot be trusted after the verifier transition.
            row.code_hash, row.demo_code = None, None
            await service.commit(db)
            raise HTTPException(410, "EMAIL_CODE_EXPIRED")
        if not hmac.compare_digest(
            row.code_hash, code_verifier(service.settings, row, match[1], body.code)
        ):
            row.code_failures += 1
            row.failures = failures + [stamp]
            if row.code_failures >= 5 or len(row.failures) >= 10:
                row.code_hash, row.demo_code = None, None
            await service.commit(db)
            raise HTTPException(422, "EMAIL_CODE_INVALID")
        row.email_verified, row.code_hash, row.demo_code = True, None, None
        service.audit(db, account, "wallet_email_verified", application_id, "VERIFIED")
        await service.commit(db)
        return view(row)


@router.post("/{application_id}/internal-approvals", response_model=OnboardingView)
async def internal_approval(
    application_id: str,
    body: DecisionInput,
    request: Request,
    identity: Identity,
):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer")
    if not body.reason.strip():
        raise HTTPException(422, "REASON_REQUIRED")
    async with service.database.session_factory() as db:
        app, _ = await application(db, application_id, account, owner=False)
        if app.applicant_account_id == account.account_id:
            raise HTTPException(403, "SELF_APPROVAL_FORBIDDEN")
        if service.settings.wallet_internal_approvers.get(app.issuer_id) != account.account_id:
            raise HTTPException(403, "INTERNAL_APPROVER_REQUIRED")
        row = await db.get(WalletOnboardingRow, application_id)
        if row is None or not row.email_verified:
            raise HTTPException(409, "EMAIL_VERIFICATION_REQUIRED")
        if row.approved_by:
            raise HTTPException(409, "ALREADY_DECIDED")
        row.internally_approved = body.decision == "APPROVE"
        row.approved_by = account.account_id
        service.audit(db, account, "wallet_internal_approval", application_id, body.decision)
        await service.commit(db)
        return view(row)


async def approved_application(db, application_id, issuer_id):
    app = await db.get(IssuerApplicationRow, application_id)
    row = await db.get(WalletOnboardingRow, application_id)
    if app is None or app.issuer_id != issuer_id:
        raise HTTPException(404, "APPLICATION_NOT_FOUND")
    if row is None or not row.email_verified or not row.internally_approved:
        raise HTTPException(409, "INSTITUTION_CHECKS_REQUIRED")
    return app, row
