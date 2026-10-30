from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from .database import AccountRow, SessionRow

COOKIE = "originproof_session"
SESSION_HOURS = 8
router = APIRouter(prefix="/v1/auth", tags=["auth"])


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class AccountView(BaseModel):
    account_id: str
    username: str
    role: str
    issuer_id: str | None
    csrf_token: str


class LogoutView(BaseModel):
    status: str = "logged_out"


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["personal", "business"]
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    terms_accepted: Literal[True]
    issuer_id: str | None = Field(default=None, max_length=128)


class RegisteredView(BaseModel):
    account_id: str
    username: str
    role: str
    issuer_id: str | None


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    try:
        scheme, rounds, salt, expected = stored.split("$")
        if scheme != "pbkdf2_sha256" or not 100_000 <= int(rounds) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


_DUMMY_PASSWORD_HASH = password_hash(secrets.token_urlsafe(32))


async def current_session(request: Request) -> tuple[AccountRow, SessionRow]:
    token = request.cookies.get(COOKIE)
    if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(401, "AUTH_REQUIRED")
    async with request.app.state.database.session_factory() as db:
        session = await db.get(SessionRow, _token_hash(token))
        if session is None:
            raise HTTPException(401, "AUTH_REQUIRED")
        expiry = session.expires_at
        if (expiry if expiry.tzinfo else expiry.replace(tzinfo=UTC)) <= datetime.now(UTC):
            raise HTTPException(401, "AUTH_REQUIRED")
        account = await db.get(AccountRow, session.account_id)
        if account is None:
            raise HTTPException(401, "AUTH_REQUIRED")
        return account, session


def require_csrf(request: Request, session: SessionRow) -> None:
    supplied = request.headers.get("X-CSRF-Token", "")
    if not supplied or not hmac.compare_digest(supplied.encode(), session.csrf_token.encode()):
        raise HTTPException(403, "CSRF_REQUIRED")


@router.post("/login", response_model=AccountView)
async def login(body: LoginInput, request: Request, response: Response) -> AccountView:
    async with request.app.state.database.session_factory() as db:
        account = await db.scalar(
            select(AccountRow).where(AccountRow.username == body.username.strip().casefold())
        )
        matches = await run_in_threadpool(
            password_matches,
            body.password,
            account.password_hash if account else _DUMMY_PASSWORD_HASH,
        )
        if account is None or not matches:
            raise HTTPException(401, "INVALID_CREDENTIALS")
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        db.add(
            SessionRow(
                token_hash=_token_hash(token),
                account_id=account.account_id,
                csrf_token=csrf_token,
                expires_at=datetime.now(UTC) + timedelta(hours=SESSION_HOURS),
            )
        )
        await db.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.session_cookie_secure or request.url.scheme == "https",
    )
    return AccountView(
        account_id=account.account_id,
        username=account.username,
        role=account.role,
        issuer_id=account.issuer_id,
        csrf_token=csrf_token,
    )


@router.post("/register", response_model=RegisteredView, status_code=201)
async def register(body: RegisterInput, request: Request) -> RegisteredView:
    """Opt-in synthetic sign-up: only reserved .invalid mail, so no real personal data."""
    from .wallet_onboarding import ROSTER  # local import: wallet_onboarding imports this module

    if not request.app.state.settings.signup_enabled:
        raise HTTPException(409, "SIGNUP_DISABLED")
    email = body.email.strip().casefold()
    match = re.fullmatch(r"[^@\s]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)", email)
    domain = match.group(1) if match else ""
    if body.kind == "business":
        # Staff of a roster institution sign up with that institution's synthetic domain.
        entry = ROSTER.get(body.issuer_id or "")
        if entry is None or domain != entry[1]:
            raise HTTPException(422, "SYNTHETIC_ROSTER_MISMATCH")
    elif body.issuer_id is not None:
        raise HTTPException(422, "MALFORMED_INPUT")
    elif not domain.endswith(".invalid"):
        raise HTTPException(422, "SYNTHETIC_EMAIL_REQUIRED")
    if not (re.search(r"[A-Za-z]", body.password) and re.search(r"[0-9]", body.password)):
        raise HTTPException(422, "WEAK_PASSWORD")
    view = RegisteredView(
        account_id=f"acct_{uuid4().hex}",
        username=email,
        role="issuer" if body.kind == "business" else "recipient",
        issuer_id=body.issuer_id if body.kind == "business" else None,
    )
    hashed = await run_in_threadpool(password_hash, body.password)
    async with request.app.state.database.session_factory() as db:
        db.add(AccountRow(**view.model_dump(), password_hash=hashed))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(409, "ACCOUNT_EXISTS") from None
    return view


@router.get("/me", response_model=AccountView)
async def me(identity: tuple[AccountRow, SessionRow] = Depends(current_session)) -> AccountView:
    account, session = identity
    return AccountView(
        account_id=account.account_id,
        username=account.username,
        role=account.role,
        issuer_id=account.issuer_id,
        csrf_token=session.csrf_token,
    )


@router.post("/logout", response_model=LogoutView)
async def logout(
    request: Request,
    response: Response,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> LogoutView:
    _, session = identity
    require_csrf(request, session)
    async with request.app.state.database.session_factory() as db:
        stored = await db.get(SessionRow, session.token_hash)
        if stored is not None:
            await db.delete(stored)
            await db.commit()
    response.delete_cookie(COOKIE)
    return LogoutView()
