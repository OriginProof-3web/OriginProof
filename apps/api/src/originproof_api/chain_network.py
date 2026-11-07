"""Public network metadata: CHAIN_TARGET, approver node labels (models, not agencies) and the
synthetic institutions that are ACTIVE on the registry right now."""

from typing import Literal

from fastapi import APIRouter, Request
from infrastructure.blockchain.network import APPROVER_NODES
from originproof_core.wallet_signatures import identifier_hash
from pydantic import BaseModel

from .wallet_onboarding import ROSTER

router = APIRouter(tags=["chain network"])


class ApproverNodeView(BaseModel):
    role: Literal["approver_1", "approver_2", "approver_3"]
    label: str
    notice: str


class ChainNetworkView(BaseModel):
    chain_target: Literal["anvil", "sepolia"]
    chain_id: int
    rpc_fallback_configured: bool
    registry_address: str | None
    approver_nodes: list[ApproverNodeView]


class ActiveIssuerView(BaseModel):
    name: str
    issuer_id: str  # identifier_hash, the value the registry stores


class ActiveIssuersView(BaseModel):
    issuers: list[ActiveIssuerView]


@router.get("/v1/chain/network", response_model=ChainNetworkView)
async def chain_network(request: Request) -> ChainNetworkView:
    # RPC URLs and manifest paths stay server-side; only the selection and labels are public.
    settings = request.app.state.settings
    return ChainNetworkView(
        chain_target=settings.chain_target,
        chain_id=settings.blockchain_chain_id,
        rpc_fallback_configured=bool(settings.blockchain_rpc_fallback_url),
        registry_address=settings.wallet_registry_address,
        approver_nodes=[ApproverNodeView(**node) for node in APPROVER_NODES],
    )


@router.get("/v1/chain/issuers", response_model=ActiveIssuersView)
async def active_issuers(request: Request) -> ActiveIssuersView:
    # Names come from the synthetic roster; ACTIVE comes only from the chain (never assumed).
    runtime = request.app.state.wallet_runtime
    found = []
    for issuer, (name, _domain) in ROSTER.items():
        hashed = identifier_hash(issuer)
        state = await runtime.rpc("issuer", hashed)
        if state is not None and state.state == "ACTIVE":
            found.append(ActiveIssuerView(name=name, issuer_id=hashed))
    return ActiveIssuersView(issuers=found)
