"""Issuer screens on the v5 wallet Registry: my chain state and key, my published notices, and
how each institution got registered (applicant, internal approver, operator 2-of-3 approvals).

The old v1 key list (/v1/issuer/keys) and v2 proof list read registries the v5 deployment does not
configure, so the web 'key management' and 'published list' screens showed chain errors.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from originproof_core.wallet_contract import ProposalView
from originproof_core.wallet_signatures import identifier_hash
from pydantic import BaseModel
from sqlalchemy import select

from .database import AccountRow, IssuerApplicationRow
from .wallet_database import WalletDocumentRow, WalletOnboardingRow, WalletProposalRow
from .wallet_documents import Identity
from .wallet_governance import proposal_view
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


class RegistrationProposal(BaseModel):
    proposal_id: str
    proposer: str
    status: Literal["PREPARED", "PENDING", "EXECUTED", "EXPIRED", "STALE"]
    approvers: list[str]


class RegistrationTrail(BaseModel):
    issuer_name: str
    applicant: str
    email_verified: bool
    internal_approver: str | None
    internally_approved: bool
    proposals: list[RegistrationProposal]
    chain_state: Literal["ACTIVE", "SUSPENDED"] | None


class RegistrationTrails(BaseModel):
    trails: list[RegistrationTrail]


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


@router.get("/registrations", response_model=RegistrationTrails)
async def registration_trails(request: Request, identity: Identity):
    """Steps done by accounts that have no screen of their own: internal approver, operators."""
    service = runtime(request)
    account = service.authorize(request, identity, mutation=False)
    if account.role != "operator" and not (account.role == "issuer" and account.issuer_id):
        raise HTTPException(403, "FORBIDDEN")
    domain = service.domain.model_dump(by_alias=True)
    async with service.database.session_factory() as db:
        query = select(IssuerApplicationRow).order_by(IssuerApplicationRow.created_at)
        if account.role == "issuer":
            query = query.where(IssuerApplicationRow.issuer_id == account.issuer_id)
        apps = list(await db.scalars(query))
        onboarding = {
            row.application_id: row
            for row in await db.scalars(
                select(WalletOnboardingRow).where(
                    WalletOnboardingRow.application_id.in_([a.application_id for a in apps])
                )
            )
        }
        # Proposals from an earlier deployment cannot be checked against this chain.
        proposals = [r for r in await db.scalars(select(WalletProposalRow)) if r.domain == domain]
        operators = service.settings.wallet_operator_addresses
        ids = {a.applicant_account_id for a in apps} | {r.account_id for r in proposals}
        ids |= {row.approved_by for row in onboarding.values() if row.approved_by}
        ids |= set(operators)
        names = dict(
            (
                await db.execute(
                    select(AccountRow.account_id, AccountRow.username).where(
                        AccountRow.account_id.in_(ids)
                    )
                )
            ).all()
        )
    by_address = {address.lower(): names.get(acc, address) for acc, address in operators.items()}
    trails = []
    for app in apps:
        issuer_hash = identifier_hash(app.issuer_id).lower()
        steps = []
        for row in proposals:
            if ProposalView.model_validate(row.payload).proposal.issuer_id.lower() != issuer_hash:
                continue
            view = await proposal_view(service, row)
            steps.append(
                RegistrationProposal(
                    proposal_id=row.proposal_id,
                    proposer=names.get(row.account_id, row.account_id),
                    status=view.status,
                    approvers=[by_address.get(a.lower(), a) for a in view.approvals],
                )
            )
        chain = await service.rpc("issuer", issuer_hash)
        checks = onboarding.get(app.application_id)
        trails.append(
            RegistrationTrail(
                issuer_name=app.issuer_name,
                applicant=names.get(app.applicant_account_id, app.applicant_account_id),
                email_verified=bool(checks and checks.email_verified),
                internal_approver=names.get(checks.approved_by)
                if checks and checks.approved_by
                else None,
                internally_approved=bool(checks and checks.internally_approved),
                proposals=steps,
                chain_state=chain.state if chain else None,
            )
        )
    return RegistrationTrails(trails=trails)
