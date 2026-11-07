from itertools import count
from typing import Any

import httpx
from eth_abi import decode, encode
from eth_utils import keccak, to_checksum_address

from .errors import BlockchainConfigurationError, BlockchainDependencyError
from .models import IssuerKeyRecord, IssuerRecord, IssuerStatus, KeyStatus


def _selector(signature: str) -> bytes:
    return keccak(text=signature)[:4]


def _bytes32(value: bytes, field: str) -> bytes:
    if len(value) != 32:
        raise BlockchainConfigurationError(f"{field} must contain exactly 32 bytes")
    return value


class JsonRpcBlockchainReader:
    """Read-only adapter for the two MVP registries using standard eth_call."""

    def __init__(
        self,
        rpc_url: str,
        issuer_registry_address: str,
        key_registry_address: str,
        *,
        timeout_seconds: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        try:
            self._issuer_registry = to_checksum_address(issuer_registry_address)
            self._key_registry = to_checksum_address(key_registry_address)
        except ValueError as exc:
            raise BlockchainConfigurationError("invalid registry address") from exc
        self._rpc_url = rpc_url
        self._timeout = timeout_seconds
        self._client = client
        self._request_ids = count(1)

    async def get_issuer(self, issuer_id: bytes) -> IssuerRecord | None:
        issuer_id = _bytes32(issuer_id, "issuer_id")
        status_raw = await self._eth_call(
            self._issuer_registry,
            _selector("issuerStatus(bytes32)") + encode(["bytes32"], [issuer_id]),
        )
        status = IssuerStatus(decode(["uint8"], status_raw)[0])
        if status is IssuerStatus.NONE:
            return None
        raw = await self._eth_call(
            self._issuer_registry,
            _selector("getIssuer(bytes32)") + encode(["bytes32"], [issuer_id]),
        )
        account, metadata_hash, returned_status = decode(["address", "bytes32", "uint8"], raw)
        if IssuerStatus(returned_status) is not status:
            raise BlockchainDependencyError("issuer state changed during chain read")
        return IssuerRecord(issuer_id, to_checksum_address(account), metadata_hash, status)

    async def get_key(self, key_id: bytes) -> IssuerKeyRecord | None:
        key_id = _bytes32(key_id, "key_id")
        status_raw = await self._eth_call(
            self._key_registry,
            _selector("keyStatus(bytes32)") + encode(["bytes32"], [key_id]),
        )
        status = KeyStatus(decode(["uint8"], status_raw)[0])
        if status is KeyStatus.NONE:
            return None
        raw = await self._eth_call(
            self._key_registry,
            _selector("getKey(bytes32)") + encode(["bytes32"], [key_id]),
        )
        issuer_id, signer, valid_from, valid_until, status_value = decode(
            ["bytes32", "address", "uint64", "uint64", "uint8"], raw
        )
        if KeyStatus(status_value) is not status:
            raise BlockchainDependencyError("key state changed during chain read")
        return IssuerKeyRecord(
            key_id,
            issuer_id,
            to_checksum_address(signer),
            valid_from,
            valid_until,
            status,
        )

    async def _eth_call(self, address: str, data: bytes) -> bytes:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": next(self._request_ids),
            "method": "eth_call",
            "params": [{"to": address, "data": f"0x{data.hex()}"}, "latest"],
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(self._rpc_url, json=payload)
            response.raise_for_status()
            body = response.json()
            if "error" in body:
                error = body["error"]
                raise BlockchainDependencyError(f"chain RPC error {error.get('code', 'unknown')}")
            result = body.get("result")
            if not isinstance(result, str) or not result.startswith("0x"):
                raise BlockchainDependencyError("chain RPC returned malformed eth_call data")
            return bytes.fromhex(result[2:])
        except (httpx.HTTPError, ValueError) as exc:
            raise BlockchainDependencyError("chain RPC is unavailable") from exc
        finally:
            if owns_client:
                await client.aclose()
