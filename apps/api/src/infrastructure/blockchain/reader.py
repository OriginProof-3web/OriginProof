"""M1 port adapter. All registry calls within one operation use the same block."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from itertools import count
from pathlib import Path

import httpx
from Crypto.Hash import keccak
from originproof_core.ports import (
    DependencyUnavailableError,
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
)


def digest(text: str) -> bytes:
    return keccak.new(digest_bits=256, data=text.encode("utf-8")).digest()


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise ValueError("invalid address")
    if int(value, 16) == 0:
        raise ValueError("zero address")
    return value


def uint(word, bits):
    value = int.from_bytes(word, "big")
    if value >= 2**bits:
        raise ValueError("noncanonical ABI integer")
    return value


class JsonRpcBlockchainReader:
    def __init__(
        self,
        rpc_url,
        manifest_path,
        *,
        issuer_ids,
        expected_chain_id=31337,
        timeout=5.0,
        client=None,
    ):
        try:
            manifest = json.loads(Path(manifest_path).read_text())
            if type(manifest["chain_id"]) is not int or manifest["chain_id"] != expected_chain_id:
                raise ValueError("wrong manifest chain")
            self._deployment_block = manifest["deployment_block"]
            if type(self._deployment_block) is not int or self._deployment_block < 0:
                raise ValueError("invalid deployment block")
            self._issuer = address(manifest["contracts"]["IssuerRegistry"]["address"])
            self._key = address(manifest["contracts"]["IssuerKeyRegistry"]["address"])
            if self._issuer.lower() == self._key.lower():
                raise ValueError("duplicate contract address")
            self._issuers = {}
            for identifier in issuer_ids:
                self._id(identifier, "iss_")
                self._issuers[digest(identifier)] = identifier
            if not self._issuers:
                raise ValueError("issuer mapping required")
        except Exception:
            raise DependencyUnavailableError("invalid blockchain configuration") from None
        self._chain_id = expected_chain_id
        self._url, self._timeout, self._client = rpc_url, timeout, client
        self._ids = count(1)

    @staticmethod
    def _id(value, prefix):
        if not isinstance(value, str) or not re.fullmatch(prefix + r"[A-Za-z0-9_-]+", value):
            raise ValueError("invalid identifier")

    async def _rpc(self, client, method, params):
        request_id = next(self._ids)
        response = await client.post(
            self._url,
            timeout=self._timeout,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            },
        )
        response.raise_for_status()
        body = response.json()
        if (
            not isinstance(body, dict)
            or body.get("jsonrpc") != "2.0"
            or body.get("id") != request_id
            or "error" in body
            or "result" not in body
        ):
            raise ValueError("invalid RPC response")
        return body["result"]

    async def _call(self, client, contract, function, identifier, block, length):
        data = digest(function)[:4] + digest(identifier)
        result = await self._rpc(
            client,
            "eth_call",
            [
                {"to": contract, "data": "0x" + data.hex()},
                block,
            ],
        )
        if not isinstance(result, str) or not re.fullmatch(r"0x[0-9a-fA-F]*", result):
            raise ValueError("invalid ABI data")
        raw = bytes.fromhex(result[2:])
        if len(raw) != length * 32:
            raise ValueError("invalid ABI length")
        return [raw[i : i + 32] for i in range(0, len(raw), 32)]

    async def _read_issuer(self, client, identifier, block):
        self._id(identifier, "iss_")
        (status,) = await self._call(
            client, self._issuer, "issuerStatus(bytes32)", identifier, block, 1
        )
        value = uint(status, 8)
        if value == 0:
            return None
        return IssuerRecord(
            issuer_id=identifier,
            status=IssuerTrustStatus({1: "ACTIVE", 2: "SUSPENDED", 3: "REVOKED"}[value]),
        )

    async def _read_key(self, client, identifier, block):
        self._id(identifier, "key_")
        (status,) = await self._call(client, self._key, "keyStatus(bytes32)", identifier, block, 1)
        value = uint(status, 8)
        if value == 0:
            return None
        state = KeyTrustStatus({1: "ACTIVE", 2: "REVOKED"}[value])
        issuer_hash, account, start, end, stored = await self._call(
            client, self._key, "getKey(bytes32)", identifier, block, 5
        )
        if uint(stored, 8) != value or any(account[:12]):
            raise ValueError("invalid key record")
        valid_from = datetime.fromtimestamp(uint(start, 64), UTC)
        valid_until = datetime.fromtimestamp(uint(end, 64), UTC)
        if valid_from >= valid_until:
            raise ValueError("invalid validity window")
        return KeyRecord(
            key_id=identifier,
            issuer_id=self._issuers[issuer_hash],
            signer=address("0x" + account[12:].hex()),
            status=state,
            valid_from=valid_from,
            valid_until=valid_until,
        )

    async def _run(self, operation, identifier, at=None):
        client = self._client or httpx.AsyncClient()
        try:
            chain = await self._rpc(client, "eth_chainId", [])
            if not isinstance(chain, str) or int(chain, 16) != self._chain_id:
                raise ValueError("wrong chain")
            block = await self._rpc(client, "eth_blockNumber", [])
            if not isinstance(block, str) or int(block, 16) < self._deployment_block:
                raise ValueError("stale manifest")
            for contract in (self._issuer, self._key):
                code = await self._rpc(client, "eth_getCode", [contract, block])
                if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", code):
                    raise ValueError("registry code missing")
            if operation == "issuer":
                return await self._read_issuer(client, identifier, block)
            key = await self._read_key(client, identifier, block)
            if operation == "key":
                return key
            if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
                raise ValueError("timezone required")
            if key is None:
                return False
            issuer = await self._read_issuer(client, key.issuer_id, block)
            return (
                issuer is not None
                and issuer.status == IssuerTrustStatus.ACTIVE
                and key.status == KeyTrustStatus.ACTIVE
                and key.valid_from <= at < key.valid_until
            )
        except Exception:
            raise DependencyUnavailableError("blockchain state unavailable") from None
        finally:
            if self._client is None:
                await client.aclose()

    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None:
        return await self._run("issuer", issuer_id)

    async def get_key(self, key_id: str) -> KeyRecord | None:
        return await self._run("key", key_id)

    async def is_key_valid(self, key_id: str, at: datetime) -> bool:
        return await self._run("valid", key_id, at)
