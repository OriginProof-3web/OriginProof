from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from itertools import count
from typing import Protocol

import httpx

from .manifest import DeploymentManifest, load_manifest, validate_address, validate_hash
from .reader import digest, uint


class ChainOperationState(StrEnum):
    SUBMITTED = "SUBMITTED"
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
    recovery_id: str | None = None
    sender: str | None = None
    nonce: int | None = None


VerifyWrite = Callable[[httpx.AsyncClient, str], Awaitable[bool]]


@dataclass(frozen=True)
class PreparedChainWrite:
    """Serializable transaction fields plus the local final-state verifier."""

    action: str
    deployment_id: str
    chain_id: int
    sender: str
    contract: str
    data: str
    nonce: int
    recovery_id: str
    scan_from_block: int
    _verify: VerifyWrite = field(repr=False, compare=False)

    @property
    def transaction(self):
        return {
            "from": self.sender,
            "to": self.contract,
            "data": self.data,
            "gas": "0x7a120",
            "nonce": hex(self.nonce),
        }

    @property
    def recovery_reference(self):
        return {
            "action": self.action,
            "deployment_id": self.deployment_id,
            "chain_id": self.chain_id,
            "sender": self.sender,
            "contract": self.contract,
            "data": self.data,
            "nonce": self.nonce,
            "recovery_id": self.recovery_id,
            "scan_from_block": self.scan_from_block,
        }


class ChainWritePersistence(Protocol):
    async def save_prepared(self, recovery_reference: dict[str, object]) -> None: ...

    async def save_submitted(self, recovery_id: str, tx_hash: str) -> None: ...


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
        self._nonce_locks: dict[str, asyncio.Lock] = {}
        self._reserved_nonces: dict[str, set[int]] = {}

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

    async def _prepare(self, sender, contract_name, data, action, verify, nonce=None):
        sender = validate_address(sender).lower()
        contract = self._manifest.contract(contract_name).address.lower()
        client = self._client or httpx.AsyncClient()
        try:
            await self._verify_deployment(client)
            latest = await self._rpc(client, "eth_blockNumber", [])
            if not isinstance(latest, str):
                raise ValueError("invalid latest block")
            scan_from_block = int(latest, 16)
            if nonce is None:
                lock = self._nonce_locks.setdefault(sender, asyncio.Lock())
                async with lock:
                    pending = await self._rpc(
                        client, "eth_getTransactionCount", [sender, "pending"]
                    )
                    if not isinstance(pending, str):
                        raise ValueError("invalid pending nonce")
                    nonce = int(pending, 16)
                    reserved = self._reserved_nonces.setdefault(sender, set())
                    while nonce in reserved:
                        nonce += 1
                    reserved.add(nonce)
            if type(nonce) is not int or nonce < 0:
                raise ValueError("invalid nonce")
            fingerprint = "|".join(
                (
                    self._manifest.deployment_id,
                    str(self._manifest.chain_id),
                    sender,
                    str(nonce),
                    contract,
                    data,
                )
            )
            return PreparedChainWrite(
                action=action,
                deployment_id=self._manifest.deployment_id,
                chain_id=self._manifest.chain_id,
                sender=sender,
                contract=contract,
                data=data,
                nonce=nonce,
                recovery_id="txref_" + hashlib.sha256(fingerprint.encode()).hexdigest(),
                scan_from_block=scan_from_block,
                _verify=verify,
            )
        finally:
            if self._client is None:
                await client.aclose()

    async def submit_prepared(self, prepared: PreparedChainWrite):
        self._validate_prepared(prepared)
        client = self._client or httpx.AsyncClient()
        try:
            await self._verify_deployment(client)
            try:
                tx_hash = await self._rpc(client, "eth_sendTransaction", [prepared.transaction])
            except RpcRejected:
                self._release_nonce(prepared)
                return self._prepared_result(
                    prepared, ChainOperationState.FAILED, error_code="CHAIN_REVERTED"
                )
            tx_hash = validate_hash(tx_hash)
            return self._prepared_result(prepared, ChainOperationState.SUBMITTED, tx_hash=tx_hash)
        except (httpx.HTTPError, ValueError, RpcRejected):
            return self._prepared_result(
                prepared,
                ChainOperationState.UNKNOWN,
                error_code="SUBMISSION_UNKNOWN",
            )
        finally:
            if self._client is None:
                await client.aclose()

    async def confirm_prepared(self, prepared: PreparedChainWrite, tx_hash: str):
        self._validate_prepared(prepared)
        try:
            tx_hash = validate_hash(tx_hash)
        except ValueError:
            return self._prepared_result(
                prepared, ChainOperationState.UNKNOWN, error_code="INVALID_TRANSACTION_HASH"
            )
        client = self._client or httpx.AsyncClient()
        try:
            await self._verify_deployment(client)
            receipt = None
            for _ in range(self._receipt_attempts):
                receipt = await self._rpc(client, "eth_getTransactionReceipt", [tx_hash])
                if receipt is not None:
                    break
                await asyncio.sleep(self._poll_interval)
            if not isinstance(receipt, dict):
                return self._prepared_result(
                    prepared,
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    error_code="RECEIPT_UNKNOWN",
                )
            status = receipt.get("status")
            block_hex = receipt.get("blockNumber")
            block_hash = receipt.get("blockHash")
            receipt_tx_hash = receipt.get("transactionHash")
            if (
                not isinstance(status, str)
                or not isinstance(block_hex, str)
                or not isinstance(receipt_tx_hash, str)
            ):
                raise ValueError("invalid receipt")
            block_number = int(block_hex, 16)
            try:
                block_hash = validate_hash(block_hash)
                receipt_tx_hash = validate_hash(receipt_tx_hash)
            except ValueError:
                raise ValueError("invalid receipt identity") from None
            canonical = await self._rpc(client, "eth_getBlockByNumber", [hex(block_number), False])
            if (
                receipt_tx_hash != tx_hash
                or not isinstance(canonical, dict)
                or canonical.get("hash", "").lower() != block_hash
            ):
                return self._prepared_result(
                    prepared,
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash,
                    error_code="RECEIPT_NOT_CANONICAL",
                )
            if int(status, 16) != 1:
                self._release_nonce(prepared)
                return self._prepared_result(
                    prepared,
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
                return self._prepared_result(
                    prepared,
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash,
                    error_code="CONFIRMATION_PENDING",
                )
            if not await prepared._verify(client, hex(latest_number)):
                self._release_nonce(prepared)
                return self._prepared_result(
                    prepared,
                    ChainOperationState.UNKNOWN,
                    tx_hash=tx_hash,
                    block_number=block_number,
                    block_hash=block_hash,
                    confirmation_count=confirmations,
                    reread_block_number=latest_number,
                    error_code="STATE_NOT_CONFIRMED",
                )
            self._release_nonce(prepared)
            return self._prepared_result(
                prepared,
                ChainOperationState.CONFIRMED,
                tx_hash=tx_hash,
                block_number=block_number,
                block_hash=block_hash,
                confirmation_count=confirmations,
                reread_block_number=latest_number,
            )
        except (httpx.HTTPError, ValueError, RpcRejected):
            return self._prepared_result(
                prepared,
                ChainOperationState.UNKNOWN,
                tx_hash=tx_hash,
                error_code="DEPENDENCY_UNAVAILABLE",
            )
        finally:
            if self._client is None:
                await client.aclose()

    async def execute_prepared(
        self, prepared: PreparedChainWrite, persistence: ChainWritePersistence
    ):
        """Persist each recovery boundary before the next irreversible step."""

        try:
            await persistence.save_prepared(prepared.recovery_reference)
        except BaseException:
            # No submission has started; release even when persistence is cancelled.
            self._release_nonce(prepared)
            raise
        submitted = await self.submit_prepared(prepared)
        if submitted.tx_hash is None:
            return submitted
        try:
            await persistence.save_submitted(prepared.recovery_id, submitted.tx_hash)
        except Exception:
            return self._prepared_result(
                prepared,
                ChainOperationState.UNKNOWN,
                tx_hash=submitted.tx_hash,
                error_code="SUBMISSION_PERSISTENCE_FAILED",
            )
        if submitted.state != ChainOperationState.SUBMITTED:
            return submitted
        return await self.confirm_prepared(prepared, submitted.tx_hash)

    async def recover_prepared(self, prepared: PreparedChainWrite, tx_hash=None):
        """Recover a fixed-nonce submission without creating a new transaction."""

        self._validate_prepared(prepared)
        if tx_hash is not None:
            return await self.confirm_prepared(prepared, tx_hash)
        client = self._client or httpx.AsyncClient()
        try:
            await self._verify_deployment(client)
            latest = await self._rpc(client, "eth_blockNumber", [])
            if not isinstance(latest, str):
                raise ValueError("invalid latest block")
            tags = [hex(number) for number in range(prepared.scan_from_block, int(latest, 16) + 1)]
            tags.append("pending")
            for tag in tags:
                block = await self._rpc(client, "eth_getBlockByNumber", [tag, True])
                if not isinstance(block, dict):
                    continue
                transactions = block.get("transactions", [])
                if not isinstance(transactions, list):
                    raise ValueError("invalid block transactions")
                for transaction in transactions:
                    if self._matches_prepared(transaction, prepared):
                        recovered_hash = validate_hash(transaction.get("hash"))
                        return await self.confirm_prepared(prepared, recovered_hash)
            return self._prepared_result(
                prepared,
                ChainOperationState.UNKNOWN,
                error_code="SUBMISSION_NOT_FOUND",
            )
        except (httpx.HTTPError, ValueError, RpcRejected):
            return self._prepared_result(
                prepared,
                ChainOperationState.UNKNOWN,
                error_code="DEPENDENCY_UNAVAILABLE",
            )
        finally:
            if self._client is None:
                await client.aclose()

    def restore_prepared(self, prepared: PreparedChainWrite, recovery_reference):
        """Restore the original scan boundary after rebuilding a verifier on restart."""

        self._validate_prepared(prepared)
        if not isinstance(recovery_reference, dict):
            raise ValueError("invalid recovery reference")
        stored_scan = recovery_reference.get("scan_from_block")
        if type(stored_scan) is not int or stored_scan < 0:
            raise ValueError("invalid recovery block")
        expected = prepared.recovery_reference
        expected["scan_from_block"] = stored_scan
        if recovery_reference != expected:
            raise ValueError("recovery reference does not match prepared transaction")
        return replace(prepared, scan_from_block=stored_scan)

    def _validate_prepared(self, prepared):
        if (
            not isinstance(prepared, PreparedChainWrite)
            or prepared.deployment_id != self._manifest.deployment_id
            or prepared.chain_id != self._manifest.chain_id
            or prepared.contract
            not in {
                self._manifest.contract("IssuerRegistry").address.lower(),
                self._manifest.contract("IssuerKeyRegistry").address.lower(),
            }
        ):
            raise ValueError("prepared transaction does not match deployment")

    def _release_nonce(self, prepared):
        reserved = self._reserved_nonces.get(prepared.sender)
        if reserved is not None:
            reserved.discard(prepared.nonce)

    @staticmethod
    def _matches_prepared(transaction, prepared):
        if not isinstance(transaction, dict):
            return False
        try:
            nonce = int(transaction.get("nonce", ""), 16)
        except (TypeError, ValueError):
            return False
        return (
            str(transaction.get("from", "")).lower() == prepared.sender.lower()
            and str(transaction.get("to", "")).lower() == prepared.contract.lower()
            and str(transaction.get("input", "")).lower() == prepared.data.lower()
            and nonce == prepared.nonce
        )

    def _prepared_result(self, prepared, state, **values):
        return self._result(
            state,
            recovery_id=prepared.recovery_id,
            sender=prepared.sender,
            nonce=prepared.nonce,
            **values,
        )

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

    async def prepare_register_issuer(
        self, sender, issuer_id, issuer_account, metadata_hash, *, nonce=None
    ):
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

        return await self._prepare(sender, "IssuerRegistry", data, "register_issuer", verify, nonce)

    async def register_issuer(self, sender, issuer_id, issuer_account, metadata_hash):
        prepared = await self.prepare_register_issuer(
            sender, issuer_id, issuer_account, metadata_hash
        )
        submitted = await self.submit_prepared(prepared)
        if submitted.state != ChainOperationState.SUBMITTED:
            return submitted
        return await self.confirm_prepared(prepared, submitted.tx_hash)

    async def _prepare_issuer_status_write(
        self, sender, issuer_id, function, expected_status, action, nonce=None
    ):
        data = _call_data(function, _identifier(issuer_id, "iss_"))

        async def verify(client, block):
            return await self._expect_issuer(client, block, issuer_id, expected_status)

        return await self._prepare(sender, "IssuerRegistry", data, action, verify, nonce)

    async def _issuer_status_write(self, sender, issuer_id, function, expected_status, action):
        prepared = await self._prepare_issuer_status_write(
            sender, issuer_id, function, expected_status, action
        )
        submitted = await self.submit_prepared(prepared)
        if submitted.state != ChainOperationState.SUBMITTED:
            return submitted
        return await self.confirm_prepared(prepared, submitted.tx_hash)

    async def prepare_suspend_issuer(self, sender, issuer_id, *, nonce=None):
        return await self._prepare_issuer_status_write(
            sender, issuer_id, "suspendIssuer(bytes32)", 2, "suspend_issuer", nonce
        )

    async def suspend_issuer(self, sender, issuer_id):
        return await self._issuer_status_write(
            sender, issuer_id, "suspendIssuer(bytes32)", 2, "suspend_issuer"
        )

    async def prepare_reactivate_issuer(self, sender, issuer_id, *, nonce=None):
        return await self._prepare_issuer_status_write(
            sender, issuer_id, "reactivateIssuer(bytes32)", 1, "reactivate_issuer", nonce
        )

    async def reactivate_issuer(self, sender, issuer_id):
        return await self._issuer_status_write(
            sender, issuer_id, "reactivateIssuer(bytes32)", 1, "reactivate_issuer"
        )

    async def prepare_revoke_issuer(self, sender, issuer_id, *, nonce=None):
        return await self._prepare_issuer_status_write(
            sender, issuer_id, "revokeIssuer(bytes32)", 3, "revoke_issuer", nonce
        )

    async def revoke_issuer(self, sender, issuer_id):
        return await self._issuer_status_write(
            sender, issuer_id, "revokeIssuer(bytes32)", 3, "revoke_issuer"
        )

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

    async def prepare_register_key(
        self,
        sender,
        key_id,
        issuer_id,
        signer,
        valid_from,
        valid_until,
        *,
        nonce=None,
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

        return await self._prepare(sender, "IssuerKeyRegistry", data, "register_key", verify, nonce)

    async def register_key(
        self,
        sender,
        key_id,
        issuer_id,
        signer,
        valid_from,
        valid_until,
    ):
        prepared = await self.prepare_register_key(
            sender, key_id, issuer_id, signer, valid_from, valid_until
        )
        submitted = await self.submit_prepared(prepared)
        if submitted.state != ChainOperationState.SUBMITTED:
            return submitted
        return await self.confirm_prepared(prepared, submitted.tx_hash)

    async def prepare_revoke_key(self, sender, key_id, *, nonce=None):
        data = _call_data("revokeKey(bytes32)", _identifier(key_id, "key_"))

        async def verify(client, block):
            return await self._expect_key(client, block, key_id, 2)

        return await self._prepare(sender, "IssuerKeyRegistry", data, "revoke_key", verify, nonce)

    async def revoke_key(self, sender, key_id):
        prepared = await self.prepare_revoke_key(sender, key_id)
        submitted = await self.submit_prepared(prepared)
        if submitted.state != ChainOperationState.SUBMITTED:
            return submitted
        return await self.confirm_prepared(prepared, submitted.tx_hash)
