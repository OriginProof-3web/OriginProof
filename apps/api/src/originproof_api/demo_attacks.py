"""Demo-only attack replay for the local hackathon laptop: change one synthetic notice's stored
amount so verification shows the server DB no longer matches the issuer signature on chain.

Off unless API_DEMO_ATTACK_USERNAMES lists the signed-in account. Never set it on public servers.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from .wallet_database import WalletDocumentRow
from .wallet_documents import Identity
from .wallet_runtime import runtime

router = APIRouter(prefix="/v3/demo", tags=["demo attack (local demo only)"])

# Bank notice #10 from scripts/fixtures/wallet_demo_bulk.py; no other demo scene reads it.
TARGET_ACCOUNT = "001234500010"
AMOUNTS = {"db-tamper": 4300000, "db-restore": 430000}


@router.post("/{action}")
async def demo_attack(
    action: Literal["db-tamper", "db-restore"], request: Request, identity: Identity
):
    service = runtime(request)
    account = service.authorize(request, identity)
    if account.username not in service.settings.demo_attack_usernames:
        raise HTTPException(404, "Not Found")  # looks absent to every other account
    domain = service.domain
    async with service.database.session_factory() as db:
        rows = await db.scalars(
            select(WalletDocumentRow).where(
                WalletDocumentRow.chain_id == domain.chain_id,
                WalletDocumentRow.verifying_contract == domain.verifying_contract,
            )
        )
        row = next(
            (r for r in rows if r.content.get("payee_account_number") == TARGET_ACCOUNT), None
        )
        if row is None:
            raise HTTPException(409, "DEMO_TARGET_NOT_FOUND")
        before = row.content.get("amount_minor")
        row.content = row.content | {"amount_minor": AMOUNTS[action]}
        service.audit(db, account, "demo_" + action.replace("-", "_"), row.document_id, "DEMO")
        await service.commit(db)
        return {
            "document_id": row.document_id,
            "version": row.version,
            "original_amount": AMOUNTS["db-restore"],
            "amount_before": before,
            "amount_after": AMOUNTS[action],
        }
