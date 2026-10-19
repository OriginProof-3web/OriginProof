"""Create prepared synthetic login accounts without putting passwords in arguments or Git."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import secrets
import stat
from pathlib import Path
from uuid import uuid4

from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, Database
from originproof_api.settings import Settings
from originproof_api.wallet_onboarding import ROSTER
from sqlalchemy import select

# Synthetic v5 roster accounts: applicant + internal approver per institution, three operators.
V5_WALLET_ACCOUNTS = (
    ("v5_bank", "issuer", "iss_origin_mock_bank"),
    ("v5_bank_approver", "issuer", "iss_origin_mock_bank"),
    ("v5_office", "issuer", "iss_origin_mock_office"),
    ("v5_office_approver", "issuer", "iss_origin_mock_office"),
    ("v5_operator1", "operator", None),
    ("v5_operator2", "operator", None),
    ("v5_operator3", "operator", None),
)
assert {issuer for _, _, issuer in V5_WALLET_ACCOUNTS if issuer} <= set(ROSTER)


async def create_account(username: str, role: str, issuer_id: str | None, password: str) -> None:
    database = Database(Settings().database_url)
    try:
        async with database.session_factory() as db:
            if await db.scalar(select(AccountRow).where(AccountRow.username == username)):
                raise SystemExit("account already exists")
            db.add(
                AccountRow(
                    account_id=f"acct_{uuid4().hex}",
                    username=username,
                    password_hash=password_hash(password),
                    role=role,
                    issuer_id=issuer_id,
                )
            )
            await db.commit()
    finally:
        await database.dispose()


async def seed_prepared(prepared, password: str) -> dict[str, str]:
    """Idempotent synthetic roles; existing credentials and onboarding are preserved."""
    database = Database(Settings().database_url)
    ids = {}
    try:
        async with database.session_factory() as db:
            for username, role, issuer_id in prepared:
                existing = await db.scalar(
                    select(AccountRow).where(AccountRow.username == username)
                )
                if existing:
                    if (existing.role, existing.issuer_id) != (role, issuer_id):
                        raise ValueError("existing account identity differs; seed stopped")
                    ids[username] = existing.account_id
                    continue
                ids[username] = f"acct_{uuid4().hex}"
                db.add(
                    AccountRow(
                        account_id=ids[username],
                        username=username,
                        role=role,
                        issuer_id=issuer_id,
                        password_hash=password_hash(password),
                    )
                )
            await db.commit()
    finally:
        await database.dispose()
    return ids


async def seed_p0(password: str) -> None:
    settings = Settings()
    await seed_prepared(
        (
            ("operator", "operator", None),
            ("bank", "issuer", settings.finals_payment_issuer_id),
            ("office", "issuer", settings.finals_document_issuer_id),
            ("recipient", "recipient", None),
            ("recipient_other", "recipient", None),
        ),
        password,
    )


def v5_wallet_env(ids: dict[str, str]) -> list[str]:
    """Settings lines for the seeded accounts; approver wallet addresses come from deployment."""
    approvers = {
        "iss_origin_mock_bank": ids["v5_bank_approver"],
        "iss_origin_mock_office": ids["v5_office_approver"],
    }
    operators = {ids[f"v5_operator{n}"]: f"<approver{n} wallet address>" for n in (1, 2, 3)}
    return [
        "API_WALLET_INTERNAL_APPROVERS=" + json.dumps(approvers, separators=(",", ":")),
        "API_WALLET_OPERATOR_ADDRESSES=" + json.dumps(operators, separators=(",", ":")),
    ]


def synthetic_password(path: Path) -> str:
    """Local-only seed credential survives restarts; never printed or passed in argv."""
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    root_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(root_fd)
        if info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise ValueError("seed credential directory must be owned and private")
        try:
            fd = os.open(
                path.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=root_fd,
            )
        except FileExistsError:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
            with os.fdopen(fd) as stream:
                info = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or (stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid())
                ):
                    raise ValueError("unsafe seed credential file") from None
                value = json.load(stream)["password"]
                if not isinstance(value, str) or len(value) < 12:
                    raise ValueError("invalid seed credential") from None
                return value
        password = secrets.token_urlsafe(24)
        with os.fdopen(fd, "w") as stream:
            json.dump({"password": password}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(root_fd)
        return password
    finally:
        os.close(root_fd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", nargs="?")
    parser.add_argument("role", nargs="?", choices=["operator", "issuer", "recipient"])
    parser.add_argument("--issuer-id")
    parser.add_argument("--p0", action="store_true")
    parser.add_argument("--v5-wallet", action="store_true")
    args = parser.parse_args()
    if args.v5_wallet:
        password = synthetic_password(Path(Settings().signer_directory) / "test-accounts.json")
        ids = asyncio.run(seed_prepared(V5_WALLET_ACCOUNTS, password))
        print("v5 wallet accounts ready; local credential file: test-accounts.json (0600)")
        print("\n".join(v5_wallet_env(ids)))
        return
    if args.p0:
        password = synthetic_password(Path(Settings().signer_directory) / "test-accounts.json")
        asyncio.run(seed_p0(password))
        print("P0 synthetic accounts ready; local credential file: test-accounts.json (0600)")
        return
    if not args.username or not args.role:
        parser.error("username and role are required unless --p0 is used")
    if (args.role == "issuer") != bool(args.issuer_id):
        parser.error("--issuer-id is required only for issuer accounts")
    username = args.username.strip().casefold()
    if not username:
        parser.error("username is required")
    password = getpass.getpass("Password: ")
    if len(password) < 12 or password != getpass.getpass("Confirm password: "):
        parser.error("passwords must match and have at least 12 characters")
    asyncio.run(create_account(username, args.role, args.issuer_id, password))
    print(f"created {username} ({args.role})")


if __name__ == "__main__":
    main()
