import asyncio
import json

import httpx
import pytest
from infrastructure.blockchain.reader import digest
from infrastructure.blockchain.writer import ChainOperationState, JsonRpcBlockchainWriter

ISSUER = "iss_origin_mock_bank"
KEY = "key_origin_mock_bank_002"
ACCOUNT = "0x" + "77" * 20
SIGNER = "0x" + "88" * 20
METADATA = "0x" + "99" * 32
GENESIS_HASH = "0x" + "aa" * 32
DEPLOYMENT_HASH = "0x" + "bb" * 32
RECEIPT_HASH = "0x" + "cc" * 32
TX_HASH = "0x" + "dd" * 32
DEPLOYMENT_ID = "dep_" + "ee" * 32


def word(value):
    return value.to_bytes(32, "big").hex()


@pytest.fixture
def manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "chain_id": 31337,
                "genesis_block_hash": GENESIS_HASH,
                "deployment_id": DEPLOYMENT_ID,
                "deployment_block": 1,
                "deployment_block_hash": DEPLOYMENT_HASH,
                "source_commit_sha": "f" * 40,
                "contracts": {
                    "IssuerRegistry": {
                        "address": "0x" + "22" * 20,
                        "constructor_arguments": ["0x" + "44" * 20],
                        "abi_sha256": "1" * 64,
                    },
                    "IssuerKeyRegistry": {
                        "address": "0x" + "33" * 20,
                        "constructor_arguments": ["0x" + "44" * 20, "0x" + "22" * 20],
                        "abi_sha256": "2" * 64,
                    },
                },
                "roles": {
                    "registry_admin": "0x" + "44" * 20,
                    "issuer_manager": "0x" + "55" * 20,
                    "key_manager": "0x" + "66" * 20,
                    "issuer_account": ACCOUNT,
                },
            }
        )
    )
    return path


def transport(fault=None, sends=None, timeline=None):
    state = {"selector": None, "canonical_reads": 0}

    def handle(request):
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        if fault == "transport" and method == "eth_sendTransaction":
            raise httpx.ConnectError("ambiguous transport failure", request=request)
        if method == "eth_chainId":
            result = hex(31337)
        elif method == "eth_getBlockByNumber":
            if fault == "canonical_rpc" and params[0] == "0x9":
                raise httpx.ConnectError("canonical lookup failed", request=request)
            hashes = {
                "0x0": GENESIS_HASH,
                "0x1": DEPLOYMENT_HASH,
                "0x8": "0x" + "ab" * 32,
                "0x9": RECEIPT_HASH,
            }
            if params[0] == "0x9":
                state["canonical_reads"] += 1
                if fault == "reorg_after_reread" and state["canonical_reads"] >= 3:
                    hashes["0x9"] = "0x" + "12" * 32
                if fault == "reread_block_reorg" and state["canonical_reads"] >= 2:
                    hashes["0x9"] = "0x" + "12" * 32
            transactions = []
            if fault == "recover_without_hash" and params == ["0x9", True]:
                transactions = [
                    {
                        "hash": TX_HASH,
                        "from": "0x" + "55" * 20,
                        "to": "0x" + "22" * 20,
                        "input": (
                            "0x"
                            + digest("registerIssuer(bytes32,address,bytes32)")[:4].hex()
                            + digest(ISSUER).hex()
                            + "00" * 12
                            + ACCOUNT[2:]
                            + METADATA[2:]
                        ),
                        "nonce": "0x5",
                    }
                ]
            result = {
                "hash": hashes.get(params[0], RECEIPT_HASH),
                "transactions": transactions,
            }
        elif method == "eth_getCode":
            result = "0x6000"
        elif method == "eth_getTransactionCount":
            result = "0x5"
        elif method == "eth_sendTransaction":
            if timeline is not None:
                timeline.append("send")
            if sends is not None:
                sends.append(params[0])
            state["selector"] = params[0]["data"][2:10]
            if fault == "rejected":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "error": {"code": 3, "message": "execution reverted"},
                    },
                )
            result = TX_HASH
        elif method == "eth_getTransactionReceipt":
            if timeline is not None:
                timeline.append("receipt")
            if fault == "receipt_missing":
                result = None
            else:
                result = {
                    "transactionHash": "0x" + "11" * 32 if fault == "transaction_hash" else TX_HASH,
                    "status": "0x0" if fault == "receipt_failed" else "0x1",
                    "blockNumber": "0x8" if fault == "reread_block_reorg" else "0x9",
                    "blockHash": (
                        "0x" + "ab" * 32
                        if fault == "reread_block_reorg"
                        else "0x" + "12" * 32
                        if fault == "block_hash"
                        else RECEIPT_HASH
                    ),
                }
        elif method == "eth_blockNumber":
            result = "0x9"
        elif method == "eth_call":
            selector = params[0]["data"][2:10]
            status_by_write = {
                digest("suspendIssuer(bytes32)")[:4].hex(): 2,
                digest("reactivateIssuer(bytes32)")[:4].hex(): 1,
                digest("revokeIssuer(bytes32)")[:4].hex(): 3,
            }
            if selector == digest("getIssuer(bytes32)")[:4].hex():
                status = 0 if fault == "reread" else 1
                result = "0x" + "00" * 12 + ACCOUNT[2:] + METADATA[2:] + word(status)
            elif selector == digest("issuerStatus(bytes32)")[:4].hex():
                status = status_by_write[state["selector"]]
                result = "0x" + word(0 if fault == "reread" else status)
            elif selector == digest("getKey(bytes32)")[:4].hex():
                status = 0 if fault == "reread" else 1
                result = (
                    "0x"
                    + digest(ISSUER).hex()
                    + "00" * 12
                    + SIGNER[2:]
                    + word(100)
                    + word(200)
                    + word(status)
                )
            elif selector == digest("keyStatus(bytes32)")[:4].hex():
                result = "0x" + word(0 if fault == "reread" else 2)
            else:
                raise AssertionError("unexpected eth_call")
        else:
            raise AssertionError(f"unexpected RPC method: {method}")
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body["id"], "result": result},
        )

    return httpx.MockTransport(handle)


class FakePersistence:
    def __init__(self, fail=None, timeline=None):
        self.fail = fail
        self.timeline = timeline
        self.events = []
        self.prepared = None
        self.tx_hash = None

    async def save_prepared(self, recovery_reference):
        if self.timeline is not None:
            self.timeline.append("persist_prepared")
        self.events.append("prepared")
        if self.fail == "prepared":
            raise RuntimeError("database unavailable")
        self.prepared = recovery_reference

    async def save_submitted(self, recovery_id, tx_hash):
        if self.timeline is not None:
            self.timeline.append("persist_submitted")
        self.events.append("submitted")
        if self.fail == "submitted":
            raise RuntimeError("database unavailable")
        self.tx_hash = tx_hash


async def writer(manifest, fault=None, sends=None, receipt_attempts=2, timeline=None):
    client = httpx.AsyncClient(transport=transport(fault, sends, timeline))
    return (
        JsonRpcBlockchainWriter(
            "http://test",
            manifest,
            client=client,
            receipt_attempts=receipt_attempts,
            poll_interval=0,
        ),
        client,
    )


async def test_register_issuer_confirms_receipt_and_reread(manifest):
    sends = []
    adapter, client = await writer(manifest, sends=sends)
    async with client:
        result = await adapter.register_issuer("0x" + "55" * 20, ISSUER, ACCOUNT, METADATA)
    assert result.state == ChainOperationState.CONFIRMED
    assert result.tx_hash == TX_HASH
    assert result.block_number == 9
    assert result.confirmation_count == 1
    assert result.reread_block_number == 9
    assert result.deployment_id == DEPLOYMENT_ID
    assert len(sends) == 1


@pytest.mark.parametrize(
    "method,expected",
    [("suspend_issuer", 2), ("reactivate_issuer", 1), ("revoke_issuer", 3)],
)
async def test_issuer_status_writes_confirm(manifest, method, expected):
    adapter, client = await writer(manifest)
    async with client:
        result = await getattr(adapter, method)("0x" + "55" * 20, ISSUER)
    assert result.state == ChainOperationState.CONFIRMED
    assert expected in (1, 2, 3)


async def test_key_register_and_revoke_confirm(manifest):
    adapter, client = await writer(manifest)
    async with client:
        registered = await adapter.register_key(ACCOUNT, KEY, ISSUER, SIGNER, 100, 200)
        revoked = await adapter.revoke_key(ACCOUNT, KEY)
    assert registered.state == ChainOperationState.CONFIRMED
    assert revoked.state == ChainOperationState.CONFIRMED


@pytest.mark.parametrize(
    "fault,state,error",
    [
        ("rejected", ChainOperationState.FAILED, "CHAIN_REVERTED"),
        ("receipt_failed", ChainOperationState.FAILED, "CHAIN_REVERTED"),
        ("receipt_missing", ChainOperationState.UNKNOWN, "RECEIPT_UNKNOWN"),
        ("transport", ChainOperationState.UNKNOWN, "SUBMISSION_UNKNOWN"),
        ("reread", ChainOperationState.UNKNOWN, "STATE_NOT_CONFIRMED"),
        ("transaction_hash", ChainOperationState.UNKNOWN, "RECEIPT_NOT_CANONICAL"),
        ("block_hash", ChainOperationState.UNKNOWN, "RECEIPT_NOT_CANONICAL"),
        ("reorg_after_reread", ChainOperationState.UNKNOWN, "RECEIPT_NOT_CANONICAL"),
        ("reread_block_reorg", ChainOperationState.UNKNOWN, "STATE_NOT_CONFIRMED"),
        ("canonical_rpc", ChainOperationState.UNKNOWN, "DEPENDENCY_UNAVAILABLE"),
    ],
)
async def test_failure_and_ambiguous_results_are_not_confirmed(manifest, fault, state, error):
    sends = []
    adapter, client = await writer(manifest, fault=fault, sends=sends)
    async with client:
        result = await adapter.register_issuer("0x" + "55" * 20, ISSUER, ACCOUNT, METADATA)
    assert result.state == state
    assert result.error_code == error
    assert len(sends) <= 1


async def test_invalid_input_does_not_submit(manifest):
    sends = []
    adapter, client = await writer(manifest, sends=sends)
    async with client:
        with pytest.raises(ValueError, match="validity window"):
            await adapter.register_key(ACCOUNT, KEY, ISSUER, SIGNER, 200, 100)
        with pytest.raises(ValueError, match="identifier"):
            await adapter.suspend_issuer(ACCOUNT, "wrong_issuer")
    assert sends == []


async def test_persistence_failure_prevents_submission(manifest):
    sends = []
    adapter, client = await writer(manifest, sends=sends)
    store = FakePersistence(fail="prepared")
    async with client:
        prepared = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        with pytest.raises(RuntimeError, match="database unavailable"):
            await adapter.execute_prepared(prepared, store)
    assert store.events == ["prepared"]
    assert sends == []


@pytest.mark.parametrize("fault", ["transport", "invalid_block"])
async def test_failed_prepare_does_not_reserve_nonce(manifest, fault):
    base = transport()
    fail_once = True

    def handle(request):
        nonlocal fail_once
        body = json.loads(request.content)
        if body["method"] == "eth_blockNumber" and fail_once:
            fail_once = False
            if fault == "transport":
                raise httpx.ConnectError("temporary block RPC outage", request=request)
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": body["id"], "result": "invalid"},
            )
        return base.handle_request(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = JsonRpcBlockchainWriter("http://test", manifest, client=client)
        with pytest.raises((httpx.ConnectError, ValueError)):
            await adapter.prepare_suspend_issuer("0x" + "55" * 20, ISSUER)
        prepared = await adapter.prepare_suspend_issuer("0x" + "55" * 20, ISSUER)
    assert prepared.nonce == 5


async def test_concurrent_prepare_reserves_distinct_local_nonces(manifest):
    adapter, client = await writer(manifest)
    async with client:
        first, second = await asyncio.gather(
            adapter.prepare_suspend_issuer("0x" + "55" * 20, ISSUER),
            adapter.prepare_reactivate_issuer("0x" + "55" * 20, ISSUER),
        )
    assert {first.nonce, second.nonce} == {5, 6}


async def test_submission_is_persisted_before_receipt_polling(manifest):
    sends = []
    timeline = []
    adapter, client = await writer(
        manifest,
        fault="receipt_missing",
        sends=sends,
        receipt_attempts=1,
        timeline=timeline,
    )
    store = FakePersistence(timeline=timeline)
    async with client:
        prepared = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        result = await adapter.execute_prepared(prepared, store)
    assert store.events == ["prepared", "submitted"]
    assert store.tx_hash == TX_HASH
    assert result.state == ChainOperationState.UNKNOWN
    assert result.error_code == "RECEIPT_UNKNOWN"
    assert result.recovery_id == prepared.recovery_id
    assert len(sends) == 1
    assert timeline == ["persist_prepared", "send", "persist_submitted", "receipt"]


async def test_ambiguous_send_keeps_fixed_nonce_recovery_reference(manifest):
    sends = []
    adapter, client = await writer(manifest, fault="transport", sends=sends)
    store = FakePersistence()
    async with client:
        prepared = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        result = await adapter.execute_prepared(prepared, store)
    assert store.prepared == prepared.recovery_reference
    assert prepared.transaction["nonce"] == "0x5"
    assert result.state == ChainOperationState.UNKNOWN
    assert result.error_code == "SUBMISSION_UNKNOWN"
    assert result.recovery_id == prepared.recovery_id
    assert result.nonce == prepared.nonce
    assert store.tx_hash is None


async def test_submitted_hash_persistence_failure_is_unknown(manifest):
    sends = []
    adapter, client = await writer(manifest, sends=sends)
    store = FakePersistence(fail="submitted")
    async with client:
        prepared = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        result = await adapter.execute_prepared(prepared, store)
    assert result.state == ChainOperationState.UNKNOWN
    assert result.error_code == "SUBMISSION_PERSISTENCE_FAILED"
    assert result.tx_hash == TX_HASH
    assert len(sends) == 1


async def test_retry_recovers_same_submission_without_resending(manifest):
    sends = []
    adapter, client = await writer(manifest, sends=sends)
    store = FakePersistence()
    async with client:
        prepared = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        first = await adapter.execute_prepared(prepared, store)
        recovered = await adapter.recover_prepared(prepared, store.tx_hash)
    assert first.state == ChainOperationState.CONFIRMED
    assert recovered.state == ChainOperationState.CONFIRMED
    assert recovered.tx_hash == first.tx_hash
    assert recovered.nonce == first.nonce
    assert len(sends) == 1


async def test_restart_recovers_by_persisted_nonce_without_resending(manifest):
    sends = []
    adapter, client = await writer(manifest, fault="recover_without_hash", sends=sends)
    async with client:
        original = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        reference = original.recovery_reference
        rebuilt = await adapter.prepare_register_issuer(
            "0x" + "55" * 20,
            ISSUER,
            ACCOUNT,
            METADATA,
            nonce=reference["nonce"],
        )
        restored = adapter.restore_prepared(rebuilt, reference)
        recovered = await adapter.recover_prepared(restored)
    assert recovered.state == ChainOperationState.CONFIRMED
    assert recovered.tx_hash == TX_HASH
    assert recovered.recovery_id == reference["recovery_id"]
    assert sends == []


async def test_receipt_rpc_outage_then_recovery_reuses_submission(manifest):
    sends = []
    original = transport(sends=sends)
    outage = {"active": True}

    def handle(request):
        body = json.loads(request.content)
        if outage["active"] and body["method"] == "eth_getTransactionReceipt":
            raise httpx.ConnectError("temporary receipt RPC outage", request=request)
        return original.handle_request(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        adapter = JsonRpcBlockchainWriter(
            "http://test", manifest, client=client, receipt_attempts=1, poll_interval=0
        )
        store = FakePersistence()
        prepared = await adapter.prepare_register_issuer(
            "0x" + "55" * 20, ISSUER, ACCOUNT, METADATA
        )
        unknown = await adapter.execute_prepared(prepared, store)
        assert unknown.state == ChainOperationState.UNKNOWN
        assert store.tx_hash == TX_HASH
        outage["active"] = False
        recovered = await adapter.recover_prepared(prepared, store.tx_hash)
    assert recovered.state == ChainOperationState.CONFIRMED
    assert recovered.tx_hash == unknown.tx_hash == TX_HASH
    assert recovered.nonce == unknown.nonce
    assert len(sends) == 1
