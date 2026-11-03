"""2026-11-01 B retest regressions; synthetic RPC only."""

import asyncio
import json
import traceback

import httpx
import pytest
from infrastructure.blockchain.errors import BlockchainDependencyError
from infrastructure.blockchain.wallet_reconciliation import WalletReconciler
from originproof_indexer.wallet_projection import WalletProjection, journal
from sqlalchemy import create_engine, select
from test_wallet_chain import H2, TX, Chain, block
from test_wallet_log_windows import LimitedOracle, rpc_for
from test_wallet_reconciliation import PID, PROPOSAL, Oracle, proposal_logs


async def test_approval_reconciliation_reads_history_once():
    oracle = Oracle()
    logs = proposal_logs(oracle)
    oracle.install("approve", [bytes.fromhex(PID[2:])], logs[2:])
    oracle.logs = logs
    oracle.views["getProposal"] = (PROPOSAL, 2, True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(oracle.handle)) as client:
        result = await WalletReconciler(rpc_for(client)).transaction(
            TX, function="approve", arguments=oracle.intent, sender=oracle.tx["from"])
    assert result["current_state"]["executed"]
    assert sum(method == "eth_getLogs" for method, _ in oracle.calls) == 1


async def test_failed_page_cancels_slow_siblings_immediately():
    oracle = LimitedOracle(8001)
    slow_started = asyncio.Event()
    active = 0

    async def handle(request):
        nonlocal active
        body = json.loads(request.content)
        if body["method"] != "eth_getLogs":
            return oracle.handle(request)
        first = body["params"][0]["fromBlock"]
        if first == "0x1":
            await slow_started.wait()
            return httpx.Response(503)
        active += 1
        slow_started.set()
        try:
            await asyncio.sleep(1)
            return oracle.handle(request)
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rpc = rpc_for(client)
        with pytest.raises(BlockchainDependencyError):
            await asyncio.wait_for(rpc.logs(1, await rpc.snapshot()), 0.15)
        assert active == 0


async def test_concurrent_scans_share_four_rpc_slots():
    oracle = LimitedOracle(8001)
    active = peak = 0

    async def handle(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.001)
            return oracle.handle(request)
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rpc = rpc_for(client)
        head = await rpc.snapshot()
        await asyncio.gather(*(rpc_for(client).logs(1, head) for _ in range(10)))
    assert peak <= 4 and active == 0


async def test_block_validation_runs_in_bounded_parallel_batches():
    oracle = LimitedOracle(101)
    # Each block has an event and its own canonical header.
    from test_wallet_chain import make_log
    oracle.logs = [make_log(number=n, block_hash=H2) for n in range(2, 102)]
    oracle.blocks.update({hex(n): block(n, H2) for n in range(2, 102)})

    active = peak = 0

    async def handle(request):
        nonlocal active, peak
        if json.loads(request.content)["method"] != "eth_getBlockByNumber":
            return oracle.handle(request)
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.005)
            return oracle.handle(request)
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rpc = rpc_for(client)
        head = await rpc.snapshot()
        assert len(await rpc.logs(1, head)) == 100
        assert peak == 4 and active == 0


@pytest.mark.parametrize("failure", ["nested", "http"])
async def test_rpc_errors_are_sanitized_dependency_errors(failure):
    secret = "provider-secret-do-not-log"

    def handle(request):
        if failure == "nested":
            return httpx.Response(200, content="[" * 100000 + "0" + "]" * 100000)
        raise httpx.ConnectError(secret, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        rpc = rpc_for(client)
        rpc.url = "https://provider.test/" + secret
        with pytest.raises(BlockchainDependencyError) as caught:
            await rpc.rpc("eth_chainId", [])
        assert secret not in "".join(traceback.format_exception(caught.value))
        assert caught.value.__context__ is None


async def test_projection_empty_log_page_cannot_skip_receipt_event():
    chain = Chain()
    original = chain.handle

    def handle(request):
        response = original(request)
        if json.loads(request.content)["method"] == "eth_getLogs":
            return httpx.Response(200, json={**response.json(), "result": []})
        return response

    engine = create_engine("sqlite://")
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            store = WalletProjection(engine, rpc_for(client))
            store.initialize()
            with pytest.raises(BlockchainDependencyError):
                await store.sync()
            assert store.checkpoint() is None
            chain.handle = original
        async with httpx.AsyncClient(transport=httpx.MockTransport(original)) as client:
            store = WalletProjection(engine, rpc_for(client))
            assert await store.sync() == 1
            with engine.connect() as conn:
                assert len(conn.execute(select(journal)).all()) == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize("fault", ["missing", "wrong_hash", "wrong_index", "partial"])
async def test_incomplete_receipts_preserve_checkpoint(fault):
    chain = Chain()
    if fault == "missing":
        chain.receipt = None
    elif fault == "wrong_hash":
        chain.receipt["blockHash"] = "0x" + "ff" * 32
    elif fault == "wrong_index":
        chain.receipt["transactionIndex"] = "0x1"
    else:
        from test_wallet_chain import make_log
        chain.receipt["logs"] = [*chain.logs, make_log(index=1)]
    engine = create_engine("sqlite://")
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(chain.handle)) as client:
            store = WalletProjection(engine, rpc_for(client))
            store.initialize()
            with pytest.raises(BlockchainDependencyError):
                await store.sync()
            assert store.checkpoint() is None
            with engine.connect() as conn:
                assert conn.execute(select(journal)).first() is None
    finally:
        engine.dispose()


async def test_nested_json_uses_verified_fallback():
    from infrastructure.blockchain.wallet_failover import FailoverWalletRpc
    oracle = LimitedOracle(2)
    calls = []

    def handle(request):
        calls.append(request.url.host)
        if request.url.host == "primary.test":
            return httpx.Response(200, content="[" * 100000 + "0" + "]" * 100000)
        return oracle.handle(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        source = rpc_for(client)
        # Use the compiled ABI, including events and constructor.
        from test_wallet_chain import ABI
        rpc = FailoverWalletRpc(client, ("http://primary.test", "http://fallback.test"),
                                chain_id=source.chain_id, address=source.address,
                                deployment_block=source.deployment_block,
                                deployment_hash=source.deployment_hash,
                                runtime_code_hash=source.runtime_code_hash, abi=ABI)
        assert (await rpc.snapshot())["number"] == "0x2"
        assert rpc.on_fallback and calls[0] == "primary.test"
        assert calls[1:] and set(calls[1:]) == {"fallback.test"}


async def test_projection_keeps_complete_pages_and_resumes_after_failed_page():
    oracle = LimitedOracle(300)
    oracle.logs = []
    oracle.blocks = {hex(n): {**block(n, H2), "transactions": []} for n in range(2, 301)}
    from test_wallet_chain import H1
    oracle.blocks["0x1"] = block(1, H1)
    failed = True
    ranges = []

    def handle(request):
        body = json.loads(request.content)
        if body["method"] == "eth_getLogs":
            start = int(body["params"][0]["fromBlock"], 16)
            ranges.append(start)
            if failed and start > 128:
                return httpx.Response(503)
        return oracle.handle(request)

    engine = create_engine("sqlite://")
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            store = WalletProjection(engine, rpc_for(client))
            store.initialize()
            with pytest.raises(BlockchainDependencyError):
                await store.sync()
            assert store.checkpoint() == (128, H2)
            failed = False
            ranges.clear()
            assert await store.sync() == 0
            assert store.checkpoint() == (300, H2)
            assert ranges == [129, 257]
    finally:
        engine.dispose()


async def test_approval_reconciliation_fits_reported_synthetic_ten_second_budget():
    oracle = LimitedOracle(30001)
    logs = proposal_logs(oracle)
    oracle.install("approve", [bytes.fromhex(PID[2:])], logs[2:])
    oracle.logs = logs
    oracle.views["getProposal"] = (PROPOSAL, 2, True)

    async def handle(request):
        if json.loads(request.content)["method"] == "eth_getLogs":
            await asyncio.sleep(2.2)
        return oracle.handle(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await asyncio.wait_for(WalletReconciler(rpc_for(client)).transaction(
            TX, function="approve", arguments=oracle.intent, sender=oracle.tx["from"]), 10)
    assert result["current_state"]["executed"]
    assert len(oracle.ranges) == 16


async def test_shared_history_preserves_receipt_and_current_proposal_states():
    from test_wallet_chain import H3
    from test_wallet_reconciliation import OTHER, SENDER
    oracle = Oracle()
    logs = proposal_logs(oracle)
    oracle.install("approve", [bytes.fromhex(PID[2:])], [logs[1]])
    oracle.tx["from"] = oracle.receipt["from"] = OTHER
    oracle.tx["transactionIndex"] = oracle.receipt["transactionIndex"] = "0x0"
    logs[1]["transactionHash"] = TX
    for log in logs[2:]:
        log.update(blockNumber="0x3", blockHash=H3, transactionHash=H3)
    oracle.blocks["0x2"]["transactions"] = [TX]
    oracle.blocks["0x3"] = {**block(3, H3), "transactions": [H3]}
    oracle.head = "0x3"
    oracle.logs = logs
    oracle.views[(H2, "getProposal")] = (PROPOSAL, 1, False)
    oracle.views[(H3, "getProposal")] = (PROPOSAL, 2, True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(oracle.handle)) as client:
        result = await WalletReconciler(rpc_for(client)).transaction(
            TX, function="approve", arguments=oracle.intent, sender=OTHER)
    assert result["receipt_state"]["approvals"] == [OTHER]
    assert result["receipt_state"]["executed"] is False
    assert result["current_state"]["approvals"] == [OTHER, SENDER]
    assert result["current_state"]["executed"] is True
    assert sum(method == "eth_getLogs" for method, _ in oracle.calls) == 1


async def test_reorg_between_projection_pages_cannot_mix_checkpoints():
    oracle = LimitedOracle(300)
    oracle.logs = []
    oracle.blocks = {hex(n): {**block(n, H2), "transactions": []} for n in range(2, 301)}
    from test_wallet_chain import H1, H3
    oracle.blocks["0x1"] = block(1, H1)

    def handle(request):
        payload = json.loads(request.content)
        if (payload["method"] == "eth_getLogs"
                and int(payload["params"][0]["fromBlock"], 16) > 128):
            oracle.blocks["0x80"]["hash"] = H3
            oracle.blocks["0x12c"]["hash"] = H3
        return oracle.handle(request)

    engine = create_engine("sqlite://")
    try:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            store = WalletProjection(engine, rpc_for(client))
            store.initialize()
            with pytest.raises(BlockchainDependencyError):
                await store.sync()
            assert store.checkpoint() == (128, H2)
            with pytest.raises(ValueError, match="explicit rewind"):
                await store.sync()
    finally:
        engine.dispose()
