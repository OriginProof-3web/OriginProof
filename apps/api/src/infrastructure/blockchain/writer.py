from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from enum import StrEnum
from itertools import count

import httpx

from .manifest import DeploymentManifest, load_manifest, validate_address, validate_hash
from .reader import digest, uint


class ChainOperationState(StrEnum):
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ChainWriteResult:
    state: ChainOperationState
    deployment_id: str
    chain_id: int
    tx_hash: str | None = None
    block_number: int | None = None
    block_hash: str | None = None
    confirmation_count: int = 0
    reread_block_number: int | None = None
    error_code: str | None = None


class RpcRejected(RuntimeError):
    pass


def _word(value: int) -> bytes:
    if type(value) is not int or value < 0 or value >= 2**256:
        raise ValueError("invalid integer")
    return value.to_bytes(32, "big")


def _bytes32(value: str) -> bytes:
    return bytes.fromhex(validate_hash(value)[2:])


def _address_word(value: str) -> bytes:
    return bytes(12) + bytes.fromhex(validate_address(value)[2:])


def _call_data(signature: str, *arguments: bytes) -> str:
    if any(len(argument) != 32 for argument in arguments):
        raise ValueError("ABI argument must be one word")
    return "0x" + (digest(signature)[:4] + b"".join(arguments)).hex()


def _identifier(value: str, prefix: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(prefix + r"[A-Za-z0-9_-]+", value):
        raise ValueError("invalid identifier")
    return digest(value)


class JsonRpcBlockchainWriter:
    """Local-EVM writer. C owns durable request reservations and retry decisions."""

    def __init__(
        self,
        rpc_url,
        manifest_path,
        *,
        expected_chain_id=31337,
        timeout=5.0,
        client=None,
        receipt_attempts=20,
        poll_interval=0.05,
    ):
        self._manifest: DeploymentManifest = load_manifest(manifest_path, expected_chain_id)
        self._url = rpc_url
        self._timeout = timeout
        self._client = client
        self._receipt_attempts = receipt_attempts
        self._poll_interval = poll_interval
        self._ids = count(1)

    async def _rpc(self, client, method, params):
        request_id = next(self._ids)
        response = await client.post(
            self._url,
            timeout=self._timeout,
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        )
        response.raise_for_status()
        body = response.json()
        if (
            not isinstance(body, dict)
            or body.get("jsonrpc") != "2.0"
            or body.get("id") != request_id
        ):
            raise ValueError("invalid RPC response")
        if "error" in body:
            raise RpcRejected("RPC rejected transaction")
        if "result" not in body:
            raise ValueError("missing RPC result")
        return body["result"]

    async def _verify_deployment(self, client):
        chain = await self._rpc(client, "eth_chainId", [])
        if not isinstance(chain, str) or int(chain, 16) != self._manifest.chain_id:
            raise ValueError("wrong chain")
        genesis = await self._rpc(client, "eth_getBlockByNumber", ["0x0", False])
        deployed = await self._rpc(
            client,
            "eth_getBlockByNumber",
            [hex(self._manifest.deployment_block), False],
        )
        if (
            not isinstance(genesis, dict)
            or not isinstance(deployed, dict)
            or genesis.get("hash", "").lower() != self._manifest.genesis_block_hash
            or deployed.get("hash", "").lower() != self._manifest.deployment_block_hash
        ):
            raise ValueError("deployment identity mismatch")
        for name in ("IssuerRegistry", "IssuerKeyRegistry"):
            code = await self._rpc(
                client,
                "eth_getCode",
                [self._manifest.contract(name).address, "latest"],
            )
            if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", code):
                raise ValueError("registry code missing")

    async def _eth_call(self, client, contract, data, block, words):
        result = await self._rpc(client, "eth_call", [{"to": contract, "data": data}, block])
        if not isinstance(result, str) or not re.fullmatch(r"0x[0-9a-fA-F]*", result):
            raise ValueError("invalid ABI data")
        raw = bytes.fromhex(result[2:])
        if len(raw) != words * 32:
            raise ValueError("invalid ABI length")
        return [raw[index : index + 32] for index in range(0, len(raw), 32)]

    async def _submit(self, sender, contract_name, data, verify):
        sender = validate_address(sender)
        contract = self._manifest.contract(contract_name).address
        client = self._client or httpx.AsyncClient()
        tx_hash = None
        try:
            await self._verify_deployment(client)
            try:
                tx_hash = await self._rpc(
                    client,
                    "eth_sendTransaction",
                    [{"from": sender, "to": contract, "data": data, "gas": "0x7a120"}],
                )
            except RpcRejected:
                return self._result(ChainOperationState.FAILED, error_code="CHAIN_REVERTED")
            if not isinstance(tx_hash, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
                raise ValueError("invalid transaction hash")
            receipt = None
            for _ in range(self._receipt_attempts):
                receipt = await self._rpc(client, "eth_getTransactionReceipt", [tx_hash])
                if receipt is not None:
                    break
                await asyncio.sleep(self._poll_interval)
            if not isinstance(receipt, dict):
                return self._result(
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    error_code="RECEIPT_UNKNOWN",
                )
            status = receipt.get("status")
            block_hex = receipt.get("blockNumber")
            block_hash = receipt.get("blockHash")
            if not isinstance(status, str) or not isinstance(block_hex, str):
                raise ValueError("invalid receipt")
            block_number = int(block_hex, 16)
            try:
                block_hash = validate_hash(block_hash)
            except ValueError:
                raise ValueError("invalid receipt block hash") from None
            if int(status, 16) != 1:
                return self._result(
                    ChainOperationState.FAILED,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash,
                    error_code="CHAIN_REVERTED",
                )
            latest = await self._rpc(client, "eth_blockNumber", [])
            if not isinstance(latest, str):
                raise ValueError("invalid latest block")
            latest_number = int(latest, 16)
            confirmations = latest_number - block_number + 1
            if confirmations < 1:
                return self._result(
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash,
                    error_code="CONFIRMATION_PENDING",
                )
            if not await verify(client, hex(latest_number)):
                return self._result(
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash,
                    confirmation_count=confirmations,
                    reread_block_number=latest_number,
                    error_code="STATE_NOT_CONFIRMED",
                )
            return self._result(
                ChainOperationState.CONFIRMED,
                tx_hash=tx_hash,
                block_number=block_number,
                block_hash=block_hash,
                confirmation_count=confirmations,
                reread_block_number=latest_number,
            )
        except (httpx.HTTPError, ValueError, RpcRejected):
            return self._result(
                ChainOperationState.UNKNOWN,
                tx_hash=tx_hash,
                error_code="DEPENDENCY_UNAVAILABLE",
            )
        finally:
            if self._client is None:
                await client.aclose()

    def _result(self, state, **values):
        return ChainWriteResult(
            state=state,
            deployment_id=self._manifest.deployment_id,
            chain_id=self._manifest.chain_id,
            **values,
        )

    async def _expect_issuer(
        self, client, block, issuer_id, expected_status, account=None, metadata=None
    ):
        identifier = _identifier(issuer_id, "iss_")
        contract = self._manifest.contract("IssuerRegistry").address
        if account is None:
            (status,) = await self._eth_call(
                client,
                contract,
                _call_data("issuerStatus(bytes32)", identifier),
                block,
                1,
            )
            return uint(status, 8) == expected_status
        stored_account, stored_metadata, status = await self._eth_call(
            client,
            contract,
            _call_data("getIssuer(bytes32)", identifier),
            block,
            3,
        )
        return (
            stored_account == _address_word(account)
            and stored_metadata == _bytes32(metadata)
            and uint(status, 8) == expected_status
        )

    async def register_issuer(self, sender, issuer_id, issuer_account, metadata_hash):
        issuer_account = validate_address(issuer_account)
        metadata = _bytes32(metadata_hash)
        data = _call_data(
            "registerIssuer(bytes32,address,bytes32)",
            _identifier(issuer_id, "iss_"),
            _address_word(issuer_account),
            metadata,
        )

        async def verify(client, block):
            return await self._expect_issuer(
                client, block, issuer_id, 1, issuer_account, metadata_hash
            )

        return await self._submit(sender, "IssuerRegistry", data, verify)

    async def _issuer_status_write(self, sender, issuer_id, function, expected_status):
        data = _call_data(function, _identifier(issuer_id, "iss_"))

        async def verify(client, block):
            return await self._expect_issuer(client, block, issuer_id, expected_status)

        return await self._submit(sender, "IssuerRegistry", data, verify)

    async def suspend_issuer(self, sender, issuer_id):
        return await self._issuer_status_write(sender, issuer_id, "suspendIssuer(bytes32)", 2)

    async def reactivate_issuer(self, sender, issuer_id):
        return await self._issuer_status_write(sender, issuer_id, "reactivateIssuer(bytes32)", 1)

    async def revoke_issuer(self, sender, issuer_id):
        return await self._issuer_status_write(sender, issuer_id, "revokeIssuer(bytes32)", 3)

    async def _expect_key(
        self,
        client,
        block,
        key_id,
        expected_status,
        issuer_id=None,
        signer=None,
        valid_from=None,
        valid_until=None,
    ):
        identifier = _identifier(key_id, "key_")
        contract = self._manifest.contract("IssuerKeyRegistry").address
        if issuer_id is None:
            (status,) = await self._eth_call(
                client,
                contract,
                _call_data("keyStatus(bytes32)", identifier),
                block,
                1,
            )
            return uint(status, 8) == expected_status
        stored_issuer, stored_signer, start, end, status = await self._eth_call(
            client,
            contract,
            _call_data("getKey(bytes32)", identifier),
            block,
            5,
        )
        return (
            stored_issuer == _identifier(issuer_id, "iss_")
            and stored_signer == _address_word(signer)
            and uint(start, 64) == valid_from
            and uint(end, 64) == valid_until
            and uint(status, 8) == expected_status
        )

    async def register_key(
        self,
        sender,
        key_id,
        issuer_id,
        signer,
        valid_from,
        valid_until,
    ):
        signer = validate_address(signer)
        if (
            type(valid_from) is not int
            or type(valid_until) is not int
            or not 0 <= valid_from < valid_until < 2**64
        ):
            raise ValueError("invalid validity window")
        data = _call_data(
            "registerKey(bytes32,bytes32,address,uint64,uint64)",
            _identifier(key_id, "key_"),
            _identifier(issuer_id, "iss_"),
            _address_word(signer),
            _word(valid_from),
            _word(valid_until),
        )

        async def verify(client, block):
            return await self._expect_key(
                client,
                block,
                key_id,
                1,
                issuer_id,
                signer,
                valid_from,
                valid_until,
            )

        return await self._submit(sender, "IssuerKeyRegistry", data, verify)

    async def revoke_key(self, sender, key_id):
        data = _call_data("revokeKey(bytes32)", _identifier(key_id, "key_"))

        async def verify(client, block):
            return await self._expect_key(client, block, key_id, 2)

        return await self._submit(sender, "IssuerKeyRegistry", data, verify)
