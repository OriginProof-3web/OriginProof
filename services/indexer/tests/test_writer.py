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


def transport(fault=None, sends=None):
    state = {"selector": None}

    def handle(request):
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        if fault == "transport" and method == "eth_sendTransaction":
            raise httpx.ConnectError("ambiguous transport failure", request=request)
        if method == "eth_chainId":
            result = hex(31337)
        elif method == "eth_getBlockByNumber":
            result = {"hash": GENESIS_HASH if params[0] == "0x0" else DEPLOYMENT_HASH}
        elif method == "eth_getCode":
            result = "0x6000"
        elif method == "eth_sendTransaction":
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
            if fault == "receipt_missing":
                result = None
            else:
                result = {
                    "transactionHash": TX_HASH,
                    "status": "0x0" if fault == "receipt_failed" else "0x1",
                    "blockNumber": "0x9",
                    "blockHash": RECEIPT_HASH,
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


async def writer(manifest, fault=None, sends=None, receipt_attempts=2):
    client = httpx.AsyncClient(transport=transport(fault, sends))
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
        ("transport", ChainOperationState.UNKNOWN, "DEPENDENCY_UNAVAILABLE"),
        ("reread", ChainOperationState.UNKNOWN, "STATE_NOT_CONFIRMED"),
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
