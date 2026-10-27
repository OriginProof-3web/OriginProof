"""Public network metadata: CHAIN_TARGET and approver node labels (models, not agencies)."""

from typing import Literal

from fastapi import APIRouter, Request
from infrastructure.blockchain.network import APPROVER_NODES
from pydantic import BaseModel

router = APIRouter(tags=["chain network"])


class ApproverNodeView(BaseModel):
    role: Literal["approver_1", "approver_2", "approver_3"]
    label: str
    notice: str


class ChainNetworkView(BaseModel):
    chain_target: Literal["anvil", "sepolia"]
    chain_id: int
    rpc_fallback_configured: bool
    approver_nodes: list[ApproverNodeView]


@router.get("/v1/chain/network", response_model=ChainNetworkView)
async def chain_network(request: Request) -> ChainNetworkView:
    # RPC URLs and manifest paths stay server-side; only the selection and labels are public.
    settings = request.app.state.settings
    return ChainNetworkView(
        chain_target=settings.chain_target,
        chain_id=settings.blockchain_chain_id,
        rpc_fallback_configured=bool(settings.blockchain_rpc_fallback_url),
        approver_nodes=[ApproverNodeView(**node) for node in APPROVER_NODES],
    )
