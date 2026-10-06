"""Create prepared synthetic login accounts without putting passwords in arguments or Git."""

from __future__ import annotations

import argparse
import asyncio
import getpass
from uuid import uuid4

from originproof_api.accounts import password_hash
from originproof_api.database import AccountRow, Database
from originproof_api.settings import Settings
from sqlalchemy import select


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("role", choices=["operator", "issuer", "recipient"])
    parser.add_argument("--issuer-id")
    args = parser.parse_args()
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
