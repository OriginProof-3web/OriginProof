import httpx
import pytest
import respx
from eth_abi import encode
from infrastructure.blockchain.errors import (
    BlockchainConfigurationError,
    BlockchainDependencyError,
)
from infrastructure.blockchain.models import IssuerStatus, KeyStatus
from infrastructure.blockchain.rpc_reader import JsonRpcBlockchainReader

RPC_URL = "http://chain.test"
ISSUER_REGISTRY = "0x0000000000000000000000000000000000000001"
KEY_REGISTRY = "0x0000000000000000000000000000000000000002"


@respx.mock
async def test_reads_issuer_and_key() -> None:
    issuer_id = b"i" * 32
    key_id = b"k" * 32
    account = "0x0000000000000000000000000000000000000011"
    signer = "0x0000000000000000000000000000000000000022"
    route = respx.post(RPC_URL)
    route.side_effect = [
        httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x" + encode(["uint8"], [1]).hex()},
        ),
        httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "result": "0x"
                + encode(["address", "bytes32", "uint8"], [account, b"m" * 32, 1]).hex(),
            },
        ),
        httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 3, "result": "0x" + encode(["uint8"], [1]).hex()},
        ),
        httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "result": "0x"
                + encode(
                    ["bytes32", "address", "uint64", "uint64", "uint8"],
                    [issuer_id, signer, 100, 200, 1],
                ).hex(),
            },
        ),
    ]
    reader = JsonRpcBlockchainReader(RPC_URL, ISSUER_REGISTRY, KEY_REGISTRY)

    issuer = await reader.get_issuer(issuer_id)
    key = await reader.get_key(key_id)

    assert issuer is not None and issuer.status is IssuerStatus.ACTIVE
    assert key is not None and key.status is KeyStatus.ACTIVE
    assert key.issuer_id == issuer_id


@respx.mock
async def test_missing_issuer_returns_none_without_reverting_getter_call() -> None:
    respx.post(RPC_URL).mock(
        return_value=httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x" + encode(["uint8"], [0]).hex()},
        )
    )
    reader = JsonRpcBlockchainReader(RPC_URL, ISSUER_REGISTRY, KEY_REGISTRY)
    assert await reader.get_issuer(b"i" * 32) is None


async def test_rejects_invalid_identifier_before_rpc() -> None:
    reader = JsonRpcBlockchainReader(RPC_URL, ISSUER_REGISTRY, KEY_REGISTRY)
    with pytest.raises(BlockchainConfigurationError):
        await reader.get_issuer(b"short")


@respx.mock
async def test_maps_rpc_error_to_safe_dependency_error() -> None:
    respx.post(RPC_URL).mock(
        return_value=httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "x"}}
        )
    )
    reader = JsonRpcBlockchainReader(RPC_URL, ISSUER_REGISTRY, KEY_REGISTRY)
    with pytest.raises(BlockchainDependencyError, match="RPC error"):
        await reader.get_issuer(b"i" * 32)
