"""Synthetic JSON-RPC and SQLite tests; no live EVM/API connection is claimed."""

import copy
import json
from pathlib import Path

import httpx
import pytest
from eth_abi import encode
from eth_utils import keccak
from infrastructure.blockchain.errors import BlockchainDependencyError
from infrastructure.blockchain.wallet_rpc import WalletRpc, signature
from originproof_indexer.wallet_projection import WalletProjection, cursors, journal
from sqlalchemy import create_engine, insert, select

ROOT = Path(__file__).resolve().parents[3]
ABI = json.loads((ROOT / "packages/contracts/abi/OriginProofWalletRegistry.json").read_text())
ADDRESS = "0x" + "12" * 20
SENDER = "0x" + "34" * 20
H1, H2, H3, TX = ["0x" + x * 32 for x in ("11", "22", "33", "aa")]
CODE = b"runtime"


def block(number, block_hash):
    return {"number": hex(number), "hash": block_hash, "timestamp": "0x64",
            "transactions": [TX] if number >= 2 else []}


def make_log(name="ProposalApproved", number=2, block_hash=H2, index=0):
    entry = next(x for x in ABI if x.get("name") == name and x["type"] == "event")
    topics, data = ["0x" + keccak(text=signature(entry)).hex()], []
    for field in entry["inputs"]:
        value = {"bytes32": b"x" * 32, "address": SENDER, "uint8": 1, "uint64": 1}[field["type"]]
        if field["indexed"]:
            topics.append("0x" + encode([field["type"]], [value]).hex())
        else:
            data.append((field["type"], value))
    return {
        "address": ADDRESS,
        "topics": topics,
        "data": "0x" + encode([x[0] for x in data], [x[1] for x in data]).hex(),
        "blockNumber": hex(number),
        "blockHash": block_hash,
        "transactionHash": TX,
        "logIndex": hex(index),
        "removed": False,
    }


class Chain:
    def __init__(self):
        self.blocks = {"0x1": block(1, H1), "0x2": block(2, H2)}
        self.head = "0x2"
        self.logs = [make_log()]
        entry = next(x for x in ABI if x.get("name") == "approve")
        self.tx = {
            "hash": TX,
            "to": ADDRESS,
            "from": SENDER,
            "chainId": "0x7a69",
            "value": "0x0",
            "blockHash": H2,
            "blockNumber": "0x2",
            "transactionIndex": "0x0",
            "input": "0x"
            + (keccak(text=signature(entry))[:4] + encode(["bytes32"], [b"x" * 32])).hex(),
        }
        self.receipt = {
            "transactionHash": TX,
            "to": ADDRESS,
            "from": SENDER,
            "blockHash": H2,
            "blockNumber": "0x2",
            "status": "0x1",
            "transactionIndex": "0x0",
            "logs": self.logs,
        }
        self.calls = []
        self.override = None
        self.call_result = "0x" + encode(["uint256"], [5]).hex()

    def handle(self, request):
        payload = json.loads(request.content)
        method, params = payload["method"], payload["params"]
        self.calls.append((method, params))
        results = {
            "eth_chainId": lambda: "0x7a69",
            "eth_getBlockByNumber": lambda: self.blocks[
                self.head if params[0] == "latest" else params[0]
            ],
            "eth_getCode": lambda: "0x" + CODE.hex(),
            "eth_call": lambda: self.call_result,
            "eth_getLogs": lambda: self.logs,
            "eth_getTransactionByHash": lambda: self.tx,
            "eth_getTransactionReceipt": lambda: self.receipt,
        }
        result = results[method]()
        body = {"jsonrpc": "2.0", "id": payload["id"], "result": result}
        if self.override:
            body = self.override(method, body)
        return httpx.Response(200, json=body)


@pytest.fixture
async def setup():
    chain = Chain()
    async with httpx.AsyncClient(transport=httpx.MockTransport(chain.handle)) as client:
        rpc = WalletRpc(
            client,
            "http://chain.test",
            chain_id=31337,
            address=ADDRESS,
            deployment_block=1,
            deployment_hash=H1,
            runtime_code_hash="0x" + keccak(CODE).hex(),
            abi=ABI,
        )
        yield chain, rpc


async def test_hash_pinned_read_uses_generated_abi(setup):
    chain, rpc = setup
    head = await rpc.snapshot()
    assert await rpc.call("nextNonce", [b"x" * 32], head) == (5,)
    call = next(params for method, params in chain.calls if method == "eth_call")
    assert call[1] == {"blockHash": H2, "requireCanonical": True}
    assert call[0]["data"][:10] == "0x" + keccak(text="nextNonce(bytes32)")[:4].hex()


@pytest.mark.parametrize("name", [x["name"] for x in ABI if x["type"] == "event"])
async def test_all_seven_events_from_compiled_abi(setup, name):
    _, rpc = setup
    result = rpc.decode_log(make_log(name))
    assert result["name"] == name
    entry = next(x for x in ABI if x.get("name") == name)
    assert set(result["arguments"]) == {x["name"] for x in entry["inputs"]}


@pytest.mark.parametrize(
    "method,result",
    [
        ("eth_chainId", "0x1"),
        ("eth_getCode", "0x"),
        ("eth_getCode", "0xdeadbeef"),
        ("eth_getBlockByNumber", None),
    ],
)
async def test_wrong_deployment_never_falls_back(setup, method, result):
    chain, rpc = setup
    chain.override = lambda name, body: {**body, "result": result} if name == method else body
    with pytest.raises(BlockchainDependencyError):
        await rpc.snapshot()


@pytest.mark.parametrize(
    "change",
    [
        lambda body: {**body, "id": -1},
        lambda body: {**body, "error": {"code": -32000}},
        lambda body: [],
        lambda body: {"jsonrpc": "2.0", "id": body["id"]},
    ],
)
async def test_rpc_errors_are_dependency_failures(setup, change):
    chain, rpc = setup
    chain.override = lambda _, body: change(body)
    with pytest.raises(BlockchainDependencyError):
        await rpc.snapshot()


@pytest.mark.parametrize(
    "mutation",
    [
        {"removed": True},
        {"address": SENDER},
        {"blockHash": H3},
        {"blockNumber": "0x3"},
        {"data": "0x"},
        {"topics": []},
    ],
)
async def test_invalid_event_page_fails(setup, mutation):
    chain, rpc = setup
    head = await rpc.snapshot()
    chain.logs = [{**make_log(), **mutation}]
    with pytest.raises(BlockchainDependencyError):
        await rpc.logs(1, head)


async def test_duplicate_logs_fail(setup):
    chain, rpc = setup
    head = await rpc.snapshot()
    chain.logs *= 2
    with pytest.raises(BlockchainDependencyError):
        await rpc.logs(1, head)


async def test_reorg_after_pinned_read_fails(setup):
    chain, rpc = setup
    head = await rpc.snapshot()
    chain.blocks["0x2"] = block(2, H3)
    with pytest.raises(BlockchainDependencyError):
        await rpc.call("nextNonce", [b"x" * 32], head)


@pytest.mark.parametrize("bad", ["0x", "0x01", "0x" + "00" * 64])
async def test_bad_abi_is_dependency_error(setup, bad):
    chain, rpc = setup
    head = await rpc.snapshot()
    chain.call_result = bad
    with pytest.raises(BlockchainDependencyError):
        await rpc.call("nextNonce", [b"x" * 32], head)


async def test_direct_transaction_evidence_decodes_actual_calldata(setup):
    chain, rpc = setup
    result = await rpc.transaction_evidence(TX)
    assert result["function"] == "approve"
    assert result["arguments"] == {"proposalId": "0x" + "78" * 32}
    assert result["sender"] == SENDER
    assert result["events"][0]["name"] == "ProposalApproved"
    assert "status" not in result  # Receipt alone is not C's CONFIRMED.
    assert not any(method.startswith("eth_send") for method, _ in chain.calls)


@pytest.mark.parametrize(
    "target,patch",
    [
        ("tx", {"to": SENDER}),
        ("tx", {"chainId": "0x1"}),
        ("tx", {"value": "0x1"}),
        ("tx", {"input": "0xdeadbeef"}),
        ("tx", {"input": "0x"}),
        ("tx", {"blockHash": H3}),
        ("receipt", {"from": ADDRESS}),
        ("receipt", {"blockHash": H3}),
        ("receipt", {"status": "0x2"}),
        ("receipt", {"transactionHash": H3}),
    ],
)
async def test_direct_transaction_identity_rejections(setup, target, patch):
    chain, rpc = setup
    getattr(chain, target).update(patch)
    with pytest.raises(BlockchainDependencyError):
        await rpc.transaction_evidence(TX)


async def test_pending_and_failed_are_not_success(setup):
    chain, rpc = setup
    receipt = chain.receipt
    chain.receipt = None
    assert await rpc.transaction_evidence(TX) is None
    chain.receipt = {**receipt, "status": "0x0", "logs": []}
    assert (await rpc.transaction_evidence(TX))["receipt_status"] == 0


async def test_checkpoint_restart_and_deployment_isolation(setup, tmp_path):
    chain, rpc = setup
    engine = create_engine("sqlite:///" + str(tmp_path / "wallet.db"))
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        assert await store.sync() == 1
        assert store.checkpoint() == (2, H2)
        reopened = WalletProjection(engine, rpc)
        assert await reopened.sync() == 0
        other = copy.copy(rpc)
        other.address = SENDER
        assert WalletProjection(engine, other).checkpoint() is None
        # An older projection does not supply current state.
        chain.call_result = "0x" + encode(["uint256"], [9]).hex()
        head = await rpc.snapshot()
        assert await rpc.call("nextNonce", [b"x" * 32], head) == (9,)
    finally:
        engine.dispose()


async def test_page_rollback_preserves_checkpoint(setup):
    chain, rpc = setup
    engine = create_engine("sqlite://")
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        await store.sync()
        chain.blocks["0x3"], chain.head = block(3, H3), "0x3"
        chain.logs = [make_log(number=3, block_hash=H3)]
        # Simulate inconsistent persisted data: insertion failure must undo cursor update.
        with engine.begin() as conn:
            conn.execute(
                insert(journal).values(
                    deployment=store.deployment, block_number=3, log_index=0, payload="existing"
                )
            )
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await store.sync()
        assert store.checkpoint() == (2, H2)
    finally:
        engine.dispose()


async def test_explicit_reorg_rewind_and_replay(setup):
    chain, rpc = setup
    engine = create_engine("sqlite://")
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        await store.sync()
        chain.blocks["0x2"] = block(2, H3)
        chain.logs = [make_log(block_hash=H3)]
        with pytest.raises(ValueError, match="explicit rewind"):
            await store.sync()
        await store.rewind(1, H1)
        assert store.checkpoint() == (1, H1)
        assert await store.sync() == 1
        with engine.connect() as conn:
            rows = conn.execute(select(journal)).mappings().all()
            assert len(rows) == 1 and H3 in rows[0]["payload"]
    finally:
        engine.dispose()


@pytest.mark.parametrize("patch", [{"removed": True}, {"transactionHash": H3}])
async def test_failed_fetch_cannot_advance_checkpoint(setup, patch):
    chain, rpc = setup
    engine = create_engine("sqlite://")
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        chain.logs[0].update(patch)
        with pytest.raises(BlockchainDependencyError):
            await store.sync()
        assert store.checkpoint() is None
        with engine.connect() as conn:
            assert conn.execute(select(cursors)).first() is None
            assert conn.execute(select(journal)).first() is None
    finally:
        engine.dispose()


async def test_rewind_cannot_retain_orphan_events(setup):
    chain, rpc = setup
    engine = create_engine("sqlite://")
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        await store.sync()
        chain.blocks["0x2"] = block(2, H3)
        with pytest.raises(ValueError, match="retains orphan"):
            await store.rewind(2, H3)
        assert store.checkpoint() == (2, H2)
    finally:
        engine.dispose()


async def test_truncated_calldata_is_dependency_error(setup):
    chain, rpc = setup
    chain.tx["input"] = chain.tx["input"][:10]
    with pytest.raises(BlockchainDependencyError):
        await rpc.transaction_evidence(TX)


async def test_duplicate_receipt_logs_fail(setup):
    chain, rpc = setup
    chain.receipt["logs"] = chain.logs * 2
    with pytest.raises(BlockchainDependencyError):
        await rpc.transaction_evidence(TX)


async def test_current_read_ignores_projection(setup):
    _, rpc = setup
    result = await rpc.read("nextNonce", [b"x" * 32])
    assert result["values"] == (5,) and result["block"]["hash"] == H2


async def test_rewind_rejects_wrong_ancestor_hash(setup):
    _, rpc = setup
    engine = create_engine("sqlite://")
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        await store.sync()
        with pytest.raises(ValueError, match="ancestor hash mismatch"):
            await store.rewind(1, H3)
        assert store.checkpoint() == (2, H2)
    finally:
        engine.dispose()


async def test_regressed_rpc_head_is_not_success(setup):
    chain, rpc = setup
    engine = create_engine("sqlite://")
    try:
        store = WalletProjection(engine, rpc)
        store.initialize()
        await store.sync()
        chain.head = "0x1"
        with pytest.raises(ValueError, match="head regressed"):
            await store.sync()
        assert store.checkpoint() == (2, H2)
    finally:
        engine.dispose()


@pytest.mark.parametrize("name,args", [("not_in_abi", []), ("nextNonce", [])])
async def test_invalid_view_input_is_configuration_error(setup, name, args):
    _, rpc = setup
    from infrastructure.blockchain.errors import BlockchainConfigurationError

    with pytest.raises(BlockchainConfigurationError):
        await rpc.call(name, args, block(2, H2))


async def test_duplicate_abi_function_rejected(setup):
    _, rpc = setup
    from infrastructure.blockchain.errors import BlockchainConfigurationError

    duplicate = next(x for x in ABI if x["type"] == "function")
    with pytest.raises(BlockchainConfigurationError):
        WalletRpc(
            rpc.client,
            rpc.url,
            chain_id=31337,
            address=ADDRESS,
            deployment_block=1,
            deployment_hash=H1,
            runtime_code_hash="0x" + keccak(CODE).hex(),
            abi=ABI + [duplicate],
        )


@pytest.mark.parametrize(
    "getter,error,args",
    [
        ("getIssuer", "UnknownIssuer", [b"i" * 32]),
        ("getKey", "UnknownKey", [b"k" * 32]),
        ("getDocument", "UnknownDocument", [b"d" * 32, 1]),
        ("getProposal", "UnknownProposal", [b"p" * 32]),
    ],
)
async def test_getter_specific_absence_is_available_in_first_adapter_pr(setup, getter, error, args):
    chain, rpc = setup

    def missing(method, body):
        if method == "eth_call":
            return {
                "jsonrpc": "2.0",
                "id": body["id"],
                "error": {"code": 3, "data": "0x" + keccak(text=error + "()")[:4].hex()},
            }
        return body

    chain.override = missing
    assert (await rpc.read(getter, args))["values"] is None


def test_bigint_positions_preserve_values_above_int4(tmp_path):
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.schema import CreateTable

    assert "block_number BIGINT" in str(CreateTable(journal).compile(dialect=dialect()))
    assert "log_index BIGINT" in str(CreateTable(journal).compile(dialect=dialect()))
    assert "block_number BIGINT" in str(CreateTable(cursors).compile(dialect=dialect()))
    engine = create_engine("sqlite:///" + str(tmp_path / "bigint.db"))
    try:
        journal.metadata.create_all(engine)
        position = 2**31 + 1
        with engine.begin() as conn:
            conn.execute(
                insert(journal).values(
                    deployment="preserved", block_number=position, log_index=position, payload="{}"
                )
            )
            conn.execute(
                insert(cursors).values(deployment="preserved", block_number=position, block_hash=H1)
            )
        with engine.connect() as conn:
            row = conn.execute(select(journal)).mappings().one()
            checkpoint = conn.execute(select(cursors)).mappings().one()
        assert row["block_number"] == row["log_index"] == checkpoint["block_number"] == position
        assert row["deployment"] == checkpoint["deployment"] == "preserved"
    finally:
        engine.dispose()


async def test_log_transaction_must_belong_to_canonical_block(setup):
    chain, rpc = setup
    chain.logs[0]["transactionHash"] = H3
    head = await rpc.snapshot()
    with pytest.raises(BlockchainDependencyError):
        await rpc.logs(1, head)
