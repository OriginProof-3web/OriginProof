"""Full P0 readiness: migrations, roles, writable protected signer directory and live chain."""

import os
import stat
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select, text

from .database import AccountRow

REVISION = "20261015_0007"


async def check_ready(app):
    try:
        await app.state.database.ping()
        async with app.state.database.session_factory() as db:
            revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
            accounts = list(await db.scalars(select(AccountRow)))
        settings = app.state.settings
        roles = {row.role for row in accounts}
        issuers = {row.issuer_id for row in accounts if row.role == "issuer"}
        if (
            revision != REVISION
            or not {"operator", "recipient", "issuer"} <= roles
            or not {
                settings.finals_payment_issuer_id,
                settings.finals_document_issuer_id,
            }
            <= issuers
        ):
            raise ValueError("runtime preparation incomplete")
        if settings.wallet_registry_address:
            for issuer in issuers:
                await app.state.wallet_runtime.rpc(
                    "issuer",
                    app.state.wallet_runtime.issuer_id(
                        next(row for row in accounts if row.issuer_id == issuer)
                    ),
                )
        else:
            directory = Path(settings.signer_directory)
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            info = directory.lstat()
            if (
                not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid()
                or (stat.S_IMODE(info.st_mode) & 0o077)
                or not os.access(directory, os.W_OK)
            ):
                raise ValueError("signer directory unavailable")
        if not settings.wallet_registry_address:
            from .main import configured_blockchain_reader

            await configured_blockchain_reader(settings).get_issuer(settings.blockchain_issuer_id)
        if settings.projection_enabled and app.state.projection.status not in (
            "SYNCED",
            "WAITING_CONFIRMATIONS",
        ):
            raise ValueError("projection not ready")
    except Exception:
        raise HTTPException(503, "RUNTIME_NOT_READY") from None
