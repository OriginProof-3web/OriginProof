"""M1 port adapter. All registry calls within one operation use the same block."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import count

import httpx
from Crypto.Hash import keccak
from originproof_core.ports import (
    DependencyUnavailableError,
    IssuerRecord,
    IssuerTrustStatus,
    KeyRecord,
    KeyTrustStatus,
)

from .manifest import load_manifest, validate_address, validate_hash


@dataclass(frozen=True)
class RegistryTrustSnapshot:
    deployment_id: str
    chain_id: int
    block_number: int
    block_hash: str
    issuer: IssuerRecord | None
    key: KeyRecord | None
    key_valid_at: bool


@dataclass(frozen=True)
class ProofChainState:
    deployment_id: str
    chain_id: int
    block_number: int
    block_hash: str
    proof_id: str
    issuer_id_hash: str
    key_id_hash: str
    signing_digest: str
    subject_binding_hash: str
    issued_at: datetime
    expires_at: datetime
    single_use: bool
    revoked_at: datetime | None
    consumed_at: datetime | None
    status: str
    consumable_at: bool


def digest(text: str) -> bytes:
    return keccak.new(digest_bits=256, data=text.encode("utf-8")).digest()


def address(value):
    return validate_address(value)


@dataclass(frozen=True)
class _Endpoint:
    """One RPC URL bound to the shared client for a single read operation."""

    client: object
    url: str

    async def post(self, **kwargs):
        return await self.client.post(self.url, **kwargs)


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
            manifest = load_manifest(manifest_path, expected_chain_id)
            self._deployment_block = manifest.deployment_block
            self._deployment_block_hash = manifest.deployment_block_hash
            self.deployment_id = manifest.deployment_id
            self._issuer = manifest.contract("IssuerRegistry").address
            self._key = manifest.contract("IssuerKeyRegistry").address
            self._proof = (
                manifest.contract("ProofStatusRegistry").address
                if "ProofStatusRegistry" in manifest.contracts
                else None
            )
            self._issuers = {}
            for identifier in issuer_ids:
                self._id(identifier, "iss_")
                self._issuers[digest(identifier)] = identifier
            if not self._issuers:
                raise ValueError("issuer mapping required")
        except Exception:
            raise DependencyUnavailableError("invalid blockchain configuration") from None
        self._chain_id = expected_chain_id
        # Dual-RPC: a URL or an ordered (primary, fallback, ...) sequence. Each read operation is
        # retried whole on the next URL, so chain/genesis/deployment/code identity is re-checked.
        self._urls = (rpc_url,) if isinstance(rpc_url, str) else tuple(rpc_url or ())
        if not self._urls or not all(isinstance(url, str) and url for url in self._urls):
            raise DependencyUnavailableError("invalid blockchain configuration")
        self._timeout, self._client = timeout, client
        self._ids = count(1)

    @staticmethod
    def _id(value, prefix):
        if not isinstance(value, str) or not re.fullmatch(prefix + r"[A-Za-z0-9_-]+", value):
            raise ValueError("invalid identifier")

    async def _rpc(self, client, method, params):
        request_id = next(self._ids)
        response = await client.post(
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
            for url in self._urls:
                try:
                    return await self._run_on(_Endpoint(client, url), operation, identifier, at)
                except Exception:
                    continue
            raise DependencyUnavailableError("blockchain state unavailable")
        finally:
            if self._client is None:
                await client.aclose()

    async def _run_on(self, client, operation, identifier, at):
        try:
            chain = await self._rpc(client, "eth_chainId", [])
            if not isinstance(chain, str) or int(chain, 16) != self._chain_id:
                raise ValueError("wrong chain")
            block = await self._rpc(client, "eth_blockNumber", [])
            if not isinstance(block, str) or int(block, 16) < self._deployment_block:
                raise ValueError("stale manifest")
            # Deployment block hash commits to its ancestry; Anvil --state can regenerate genesis.
            deployed = await self._rpc(
                client, "eth_getBlockByNumber", [hex(self._deployment_block), False]
            )
            if (
                not isinstance(deployed, dict)
                or deployed.get("hash", "").lower() != self._deployment_block_hash
            ):
                raise ValueError("deployment identity mismatch")
            for contract in (self._issuer, self._key, self._proof):
                if contract is None:
                    continue
                code = await self._rpc(client, "eth_getCode", [contract, block])
                if not isinstance(code, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", code):
                    raise ValueError("registry code missing")
            if operation == "issuer":
                return await self._read_issuer(client, identifier, block)
            if operation == "proof":
                if self._proof is None or not isinstance(at, datetime) or at.tzinfo is None:
                    raise ValueError("proof registry or timezone unavailable")
                current = await self._rpc(client, "eth_getBlockByNumber", [block, False])
                block_hash = validate_hash(current.get("hash"))
                proof_hash = digest(identifier)
                (status_word,) = await self._call(
                    client, self._proof, "proofStatus(bytes32)", identifier, block, 1
                )
                status = uint(status_word, 8)
                if status not in (0, 1, 2, 3):
                    raise ValueError("invalid proof status")
                if status == 0:
                    result = None
                else:
                    words = await self._call(
                        client, self._proof, "getProof(bytes32)", identifier, block, 9
                    )
                    issued, expires = uint(words[4], 64), uint(words[5], 64)
                    revoked, consumed = uint(words[7], 64), uint(words[8], 64)
                    single_use = uint(words[6], 8)
                    if (
                        single_use not in (0, 1)
                        or not 0 <= issued < expires
                        or (status != (2 if revoked else 3 if consumed else 1))
                    ):
                        raise ValueError("invalid proof commitment")
                    data = (
                        digest("isConsumable(bytes32,uint64)")[:4]
                        + proof_hash
                        + int(at.timestamp()).to_bytes(32, "big")
                    )
                    response = await self._rpc(
                        client, "eth_call", [{"to": self._proof, "data": "0x" + data.hex()}, block]
                    )
                    if not isinstance(response, str) or not re.fullmatch(
                        r"0x[0-9a-fA-F]{64}", response
                    ):
                        raise ValueError("invalid consumable response")
                    consumable = int(response, 16)
                    if consumable not in (0, 1):
                        raise ValueError("invalid consumable flag")
                    result = ProofChainState(
                        self.deployment_id,
                        self._chain_id,
                        int(block, 16),
                        block_hash,
                        identifier,
                        *["0x" + word.hex() for word in words[:4]],
                        datetime.fromtimestamp(issued, UTC),
                        datetime.fromtimestamp(expires, UTC),
                        bool(single_use),
                        datetime.fromtimestamp(revoked, UTC) if revoked else None,
                        datetime.fromtimestamp(consumed, UTC) if consumed else None,
                        {1: "ACTIVE", 2: "REVOKED", 3: "CONSUMED"}[status],
                        bool(consumable),
                    )
                canonical = await self._rpc(client, "eth_getBlockByNumber", [block, False])
                if validate_hash(canonical.get("hash")) != block_hash:
                    raise ValueError("proof snapshot block changed")
                return result
            if operation == "snapshot":
                issuer_id, key_id = identifier
                if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("timezone required")
                current = await self._rpc(client, "eth_getBlockByNumber", [block, False])
                if not isinstance(current, dict):
                    raise ValueError("current block unavailable")
                block_hash = validate_hash(current.get("hash"))
                issuer = await self._read_issuer(client, issuer_id, block)
                key = await self._read_key(client, key_id, block)
                canonical = await self._rpc(client, "eth_getBlockByNumber", [block, False])
                if (
                    not isinstance(canonical, dict)
                    or validate_hash(canonical.get("hash")) != block_hash
                ):
                    raise ValueError("snapshot block changed")
                key_valid = (
                    issuer is not None
                    and key is not None
                    and key.issuer_id == issuer_id
                    and issuer.status == IssuerTrustStatus.ACTIVE
                    and key.status == KeyTrustStatus.ACTIVE
                    and key.valid_from <= at < key.valid_until
                )
                return RegistryTrustSnapshot(
                    deployment_id=self.deployment_id,
                    chain_id=self._chain_id,
                    block_number=int(block, 16),
                    block_hash=block_hash,
                    issuer=issuer,
                    key=key,
                    key_valid_at=key_valid,
                )
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

    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None:
        return await self._run("issuer", issuer_id)

    async def get_key(self, key_id: str) -> KeyRecord | None:
        return await self._run("key", key_id)

    async def is_key_valid(self, key_id: str, at: datetime) -> bool:
        return await self._run("valid", key_id, at)

    async def get_issuer_key_snapshot(
        self, issuer_id: str, key_id: str, at: datetime
    ) -> RegistryTrustSnapshot:
        self._id(issuer_id, "iss_")
        self._id(key_id, "key_")
        return await self._run("snapshot", (issuer_id, key_id), at)

    async def get_proof_state(self, proof_id: str, at: datetime) -> ProofChainState | None:
        self._id(proof_id, "prf_")
        return await self._run("proof", proof_id, at)
