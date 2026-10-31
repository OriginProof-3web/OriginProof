"""Provider-window regression at the real WalletRpc/Reconciler boundary (synthetic RPC)."""

import asyncio
import json

import httpx
import pytest
from eth_utils import keccak
from infrastructure.blockchain.errors import BlockchainDependencyError
from infrastructure.blockchain.wallet_reconciliation import WalletReconciler
from infrastructure.blockchain.wallet_rpc import WalletRpc
from test_wallet_chain import ABI, ADDRESS, CODE, H1, H2, block
from test_wallet_reconciliation import OTHER, PID, PROPOSAL, SENDER, Oracle, proposal_logs


class LimitedOracle(Oracle):
    def __init__(self, head=100_001, fault=None):
        super().__init__()
        self.head = hex(head)
        self.blocks[self.head] = block(head, H2)
        self.logs = proposal_logs(self)
        self.views["getProposal"] = (PROPOSAL, 2, True)
        self.ranges, self.fault = [], fault

    def handle(self, request):
        payload = json.loads(request.content)
        if payload["method"] != "eth_getLogs":
            return super().handle(request)
        query = payload["params"][0]
        start, end = int(query["fromBlock"], 16), int(query["toBlock"], 16)
        self.ranges.append((start, end))
        if end - start + 1 > 200 or (self.fault == "rpc" and start > 200):
            return httpx.Response(200, json={
                "jsonrpc": "2.0", "id": payload["id"],
                "error": {"code": -32005, "message": "provider range limit"},
            })
        response = super().handle(request)
        body = response.json()
        if self.fault == "outside_page" and start > 200:
            body["result"] = self.logs[:1]
        if self.fault == "duplicate" and start == 1:
            body["result"] *= 2
        if self.fault == "reorg" and end == int(self.head, 16):
            self.blocks[self.head] = block(end, "0x" + "ff" * 32)
        return httpx.Response(200, json=body)


def rpc_for(client):
    return WalletRpc(
        client, "http://limited.test", chain_id=31337, address=ADDRESS,
        deployment_block=1, deployment_hash=H1,
        runtime_code_hash="0x" + keccak(CODE).hex(), abi=ABI,
    )


async def test_proposal_history_above_50000_blocks_uses_bounded_rpc_requests():
    oracle = LimitedOracle()
    async with httpx.AsyncClient(transport=httpx.MockTransport(oracle.handle)) as client:
        result = await WalletReconciler(rpc_for(client)).proposal(PID)
    assert result["approvals"] == [OTHER, SENDER] and result["executed"] is True
    assert oracle.ranges == [(start, min(start + 199, 100_001))
                             for start in range(1, 100_002, 200)]


@pytest.mark.parametrize("head", [200, 201, 400, 401])
async def test_event_window_boundaries_have_no_gaps_or_duplicate_events(head):
    oracle = LimitedOracle(head)
    async with httpx.AsyncClient(transport=httpx.MockTransport(oracle.handle)) as client:
        rpc = rpc_for(client)
        logs = await rpc.logs(1, await rpc.snapshot())
    assert len(logs) == len(oracle.logs)
    assert oracle.ranges == [(start, min(start + 199, head))
                             for start in range(1, head + 1, 200)]


@pytest.mark.parametrize("fault", ["rpc", "outside_page", "duplicate", "reorg"])
async def test_failed_or_inconsistent_page_never_returns_partial_history(fault):
    oracle = LimitedOracle(401, fault)
    async with httpx.AsyncClient(transport=httpx.MockTransport(oracle.handle)) as client:
        with pytest.raises(BlockchainDependencyError):
            await WalletReconciler(rpc_for(client)).proposal(PID)


async def test_page_parallelism_is_bounded_and_cancellation_drains_requests():
    oracle = LimitedOracle(4001)
    active, peak = 0, 0

    async def handle(request):
        nonlocal active, peak
        if json.loads(request.content)["method"] != "eth_getLogs":
            return oracle.handle(request)
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.01)
            return oracle.handle(request)
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rpc = rpc_for(client)
        head = await rpc.snapshot()
        await rpc.logs(1, head)
        assert peak == 16 and active == 0 and len(oracle.ranges) == 21
        oracle.ranges.clear()
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(rpc.logs(1, head), timeout=0.001)
        assert active == 0
