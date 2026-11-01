"""Member-owned AI keys: encrypted at rest, write-only over HTTP, used only for that member."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Literal

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, HTTPException, Request
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode
from pydantic import BaseModel, ConfigDict, SecretStr
from sqlalchemy import delete, update

from .accounts import current_session, require_csrf
from .database import AccountAiKeyRow, AccountRow, SessionRow

router = APIRouter(prefix="/v1/auth/ai-key", tags=["auth"])
Provider = Literal["openai", "anthropic"]
# OpenAI's pattern excludes sk-ant- so a Claude key cannot be saved under GPT by mistake.
KEY_PATTERNS = {
    "openai": re.compile(r"sk-(?!ant-)[A-Za-z0-9_-]{20,}"),
    "anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
}


class AiKeyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Provider
    key: SecretStr


class AiKeyView(BaseModel):
    provider: Provider | None = None
    hint: str | None = None
    storage_enabled: bool
    input_tokens: int = 0
    output_tokens: int = 0
    analyses: int = 0


def _cipher(settings) -> AESGCM | None:
    secret = settings.ai_key_secret
    if secret is None or len(secret.get_secret_value()) < 32:
        return None
    return AESGCM(hashlib.sha256(secret.get_secret_value().encode()).digest())


def _bound(account_id: str, provider: str) -> bytes:
    # Ciphertext copied to another account or provider fails authentication.
    return f"{account_id}:{provider}".encode()


async def member_ai_key(app, account_id: str) -> tuple[str, str] | None:
    """Decrypt only for one running job; a stored key that cannot be read never falls back."""
    async with app.state.database.session_factory() as db:
        row = await db.get(AccountAiKeyRow, account_id)
    if row is None:
        return None
    cipher = _cipher(app.state.settings)
    if cipher is None:
        raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE)
    try:
        key = cipher.decrypt(row.nonce, row.ciphertext, _bound(account_id, row.provider))
    except InvalidTag:
        raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE) from None
    return row.provider, key.decode()


def usage_hook(usage: dict[str, int]):
    """httpx response hook: counts what the provider reports, never reads anything else."""

    async def count(response) -> None:
        if response.status_code != 200:
            return
        await response.aread()
        try:
            reported = response.json().get("usage") or {}
            usage["input"] += max(int(reported.get("input_tokens") or 0), 0)
            usage["output"] += max(int(reported.get("output_tokens") or 0), 0)
        except (ValueError, TypeError, AttributeError):
            return

    return count


async def record_usage(app, account_id: str, usage: dict[str, int]) -> None:
    if not usage["input"] and not usage["output"]:
        return
    async with app.state.database.session_factory() as db:
        await db.execute(
            update(AccountAiKeyRow)
            .where(AccountAiKeyRow.account_id == account_id)
            .values(
                input_tokens=AccountAiKeyRow.input_tokens + usage["input"],
                output_tokens=AccountAiKeyRow.output_tokens + usage["output"],
                analyses=AccountAiKeyRow.analyses + 1,
            )
        )
        await db.commit()


@router.get("", response_model=AiKeyView)
async def read_key(
    request: Request, identity: tuple[AccountRow, SessionRow] = Depends(current_session)
) -> AiKeyView:
    enabled = _cipher(request.app.state.settings) is not None
    async with request.app.state.database.session_factory() as db:
        row = await db.get(AccountAiKeyRow, identity[0].account_id)
    if row is None:
        return AiKeyView(storage_enabled=enabled)
    return AiKeyView(
        provider=row.provider,
        hint=row.hint,
        storage_enabled=enabled,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        analyses=row.analyses,
    )


@router.post("", response_model=AiKeyView)
async def save_key(
    body: AiKeyInput,
    request: Request,
    identity: tuple[AccountRow, SessionRow] = Depends(current_session),
) -> AiKeyView:
    account, session = identity
    require_csrf(request, session)
    cipher = _cipher(request.app.state.settings)
    if cipher is None:
        raise HTTPException(409, "AI_KEY_STORAGE_DISABLED")
    key = body.key.get_secret_value().strip()
    if len(key) > 300 or not KEY_PATTERNS[body.provider].fullmatch(key):
        raise HTTPException(422, "INVALID_AI_KEY")
    nonce = os.urandom(12)
    values = {
        "provider": body.provider,
        "nonce": nonce,
        "ciphertext": cipher.encrypt(
            nonce, key.encode(), _bound(account.account_id, body.provider)
        ),
        "hint": key[-4:],
        # Usage belongs to one key: replacing the key starts counting again.
        "input_tokens": 0,
        "output_tokens": 0,
        "analyses": 0,
    }
    async with request.app.state.database.session_factory() as db:
        row = await db.get(AccountAiKeyRow, account.account_id)
        if row is None:
            db.add(AccountAiKeyRow(account_id=account.account_id, **values))
        else:
            for name, value in values.items():
                setattr(row, name, value)
        await db.commit()
    return AiKeyView(provider=body.provider, hint=key[-4:], storage_enabled=True)


@router.delete("", response_model=AiKeyView)
async def delete_key(
    request: Request, identity: tuple[AccountRow, SessionRow] = Depends(current_session)
) -> AiKeyView:
    account, session = identity
    require_csrf(request, session)
    async with request.app.state.database.session_factory() as db:
        await db.execute(
            delete(AccountAiKeyRow).where(AccountAiKeyRow.account_id == account.account_id)
        )
        await db.commit()
    return AiKeyView(storage_enabled=_cipher(request.app.state.settings) is not None)
