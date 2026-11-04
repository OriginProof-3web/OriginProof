"""Issuer screens on the v5 wallet Registry: my chain state and key, my published notices.

The old v1 key list (/v1/issuer/keys) and v2 proof list read registries the v5 deployment does not
configure, so the web 'key management' and 'published list' screens showed chain errors.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from .wallet_database import WalletDocumentRow
from .wallet_documents import Identity
from .wallet_runtime import runtime

router = APIRouter(prefix="/v3/issuer", tags=["issuer views"])


class IssuerChainState(BaseModel):
    issuer_id: str
    state: Literal["ACTIVE", "SUSPENDED"]
    key_id: str
    signer: str
    key_status: Literal["ACTIVE", "RETIRED", "COMPROMISED"]
    key_registered_block: str
    block_number: str


class IssuerDocument(BaseModel):
    document_id: str
    version: int
    latest_version: int
    notice_type: str
    summary: str | None
    amount_minor: int | None
    document_number: str | None


class IssuerDocuments(BaseModel):
    documents: list[IssuerDocument]


@router.get("/state", response_model=IssuerChainState)
async def my_chain_state(request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer", mutation=False)
    issuer_hash = service.issuer_id(account)
    issuer = await service.rpc("issuer", issuer_hash)
    if issuer is None:
        raise HTTPException(404, "ISSUER_NOT_REGISTERED")
    key = await service.rpc("key", issuer.key_id)
    status = (
        "COMPROMISED"
        if key and key.compromise_block is not None
        else "RETIRED"
        if key and key.retired_block is not None
        else "ACTIVE"
    )
    return IssuerChainState(
        issuer_id=issuer_hash,
        state=issuer.state,
        key_id=issuer.key_id,
        signer=issuer.signer,
        key_status=status,
        key_registered_block=str(key.registered_block) if key else "",
        block_number=str(issuer.block_number),
    )


@router.get("/documents", response_model=IssuerDocuments)
async def my_documents(request: Request, identity: Identity):
    service = runtime(request)
    account = service.authorize(request, identity, "issuer", mutation=False)
    issuer_hash = service.issuer_id(account)
    async with service.database.session_factory() as db:
        rows = list(
            await db.scalars(
                select(WalletDocumentRow).where(
                    WalletDocumentRow.chain_id == service.domain.chain_id,
                    WalletDocumentRow.verifying_contract == service.domain.verifying_contract,
                    WalletDocumentRow.issuer_id == issuer_hash,
                )
            )
        )
    latest = {}
    for row in rows:
        latest[row.document_id] = max(latest.get(row.document_id, 0), row.version)
    # shortcut: shows stored versions only (superseded = an older version); revocation needs a
    # chain read per notice, add it when the list must show revoked notices.
    items = [
        IssuerDocument(
            document_id=row.document_id,
            version=row.version,
            latest_version=latest[row.document_id],
            notice_type=row.content.get("notice_type", ""),
            summary=row.content.get("payment_purpose") or row.content.get("title"),
            amount_minor=row.content.get("amount_minor"),
            document_number=row.content.get("document_number"),
        )
        for row in sorted(
            rows, key=lambda r: (r.message.get("issuedAt", 0), r.version), reverse=True
        )
    ]
    return IssuerDocuments(documents=items[:50])
