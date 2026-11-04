"""Demo-only attack replay for the local hackathon laptop: change one synthetic notice's stored
amount so verification shows the server DB no longer matches the issuer signature on chain.

Off unless API_DEMO_ATTACK_USERNAMES lists the signed-in account. Never set it on public servers.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from .wallet_database import WalletDocumentRow
from .wallet_documents import Identity
from .wallet_runtime import runtime

router = APIRouter(prefix="/v3/demo", tags=["demo attack (local demo only)"])

# One notice per institution from scripts/fixtures/wallet_demo_bulk.py (payee account → original
# amount); no other demo scene reads them. Tamper multiplies the amount by ten.
TARGETS = {
    "001234500010": 430000,
    "002345600002": 150000,
    "003456700002": 55000,
    "004567800002": 220000,
}


@router.post("/{action}")
async def demo_attack(
    action: Literal["db-tamper", "db-restore"],
    request: Request,
    identity: Identity,
    account: str = Query("001234500010"),
):
    service = runtime(request)
    user = service.authorize(request, identity)
    if user.username not in service.settings.demo_attack_usernames:
        raise HTTPException(404, "Not Found")  # looks absent to every other account
    if account not in TARGETS:
        raise HTTPException(404, "DEMO_TARGET_NOT_FOUND")
    original = TARGETS[account]
    amount = original * 10 if action == "db-tamper" else original
    domain = service.domain
    async with service.database.session_factory() as db:
        rows = await db.scalars(
            select(WalletDocumentRow).where(
                WalletDocumentRow.chain_id == domain.chain_id,
                WalletDocumentRow.verifying_contract == domain.verifying_contract,
            )
        )
        row = next((r for r in rows if r.content.get("payee_account_number") == account), None)
        if row is None:
            raise HTTPException(409, "DEMO_TARGET_NOT_FOUND")
        before = row.content.get("amount_minor")
        row.content = row.content | {"amount_minor": amount}
        service.audit(db, user, "demo_" + action.replace("-", "_"), row.document_id, "DEMO")
        await service.commit(db)
        return {
            "document_id": row.document_id,
            "version": row.version,
            "original_amount": original,
            "amount_before": before,
            "amount_after": amount,
        }
