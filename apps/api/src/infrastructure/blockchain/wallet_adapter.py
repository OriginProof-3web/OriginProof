"""Read-only C port adapter; deployment trust stays with WalletRpc, DTOs with C."""

from functools import wraps

from originproof_core import DependencyUnavailableError
from originproof_core.wallet_contract import (
    DocumentView,
    GovernanceProposal,
    ProposalView,
    SigningRequest,
)
from originproof_core.wallet_ports import (
    WalletDocument,
    WalletIssuer,
    WalletKey,
    WalletProposal,
    WalletTransaction,
)
from originproof_core.wallet_signatures import document_id as calculate_document_id

from .errors import BlockchainDependencyError
from .wallet_reconciliation import WalletReconciler, require
from .wallet_rpc import hex_bytes, named, quantity


def dependency_boundary(method):
    @wraps(method)
    async def wrapped(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except (BlockchainDependencyError, ValueError, TypeError, KeyError, IndexError):
            raise DependencyUnavailableError(
                "wallet evidence unavailable or inconsistent"
            ) from None

    return wrapped


def port_arguments(fields, actual):
    """Convert actual ABI uint256 words to C's decimal strings, never echo intent."""
    result = {}
    for field in fields:
        value = actual[field["name"]]
        if field["type"] == "tuple":
            value = port_arguments(field["components"], value)
        elif field["type"] == "uint256":
            value = str(value)
        result[field["name"]] = value
    return result


class WalletRegistryReadAdapter:
    """Injectable read subset; unconfigured mutation/authorization paths fail closed."""

    def __init__(self, rpc):
        self.rpc = rpc
        self.reconciler = WalletReconciler(rpc)

    def _position(self, block):
        return {
            "chain_id": str(self.rpc.chain_id),
            "verifying_contract": self.rpc.address,
            "block_number": str(quantity(block["number"])),
            "block_hash": block["hash"],
        }

    def _key(self, key_id, raw, block):
        value = named(self.rpc.functions["getKey"]["outputs"][0]["components"], raw[0])
        require(value["registeredBlock"] > 0, "key has no registration position")
        return WalletKey(
            **self._position(block),
            key_id=key_id,
            issuer_id=value["issuerId"],
            signer=value["signer"],
            registered_block=str(value["registeredBlock"]),
            retired_block=str(value["retiredBlock"]) if value["retiredBlock"] else None,
            compromise_block=str(value["compromiseBlock"]) if value["compromiseBlock"] else None,
        )

    @dependency_boundary
    async def issuer(self, issuer_id: str) -> WalletIssuer | None:
        block = await self.rpc.snapshot()
        identifier = hex_bytes(issuer_id, 32)
        raw = await self.rpc.call("getIssuer", [identifier], block)
        if raw is None:
            return None
        state, key_id, signer, metadata_hash = raw
        key_id = "0x" + key_id.hex()
        require(state in (1, 2), "invalid issuer state")
        raw_key = await self.rpc.call("getKey", [hex_bytes(key_id, 32)], block)
        require(raw_key is not None, "current key absent")
        key = self._key(key_id, raw_key, block)
        require(
            key.issuer_id == issuer_id
            and key.signer == signer.lower()
            and key.retired_block is None,
            "current issuer/key mismatch",
        )
        nonce = (await self.rpc.call("nextNonce", [identifier], block))[0]
        governance = (await self.rpc.call("governanceNonce", [identifier], block))[0]
        await self.rpc.check(block)
        return WalletIssuer(
            **self._position(block),
            issuer_id=issuer_id,
            state="ACTIVE" if state == 1 else "SUSPENDED",
            key_id=key_id,
            signer=signer,
            metadata_hash="0x" + metadata_hash.hex(),
            next_nonce=str(nonce),
            governance_nonce=str(governance),
        )

    @dependency_boundary
    async def key(self, key_id: str) -> WalletKey | None:
        block = await self.rpc.snapshot()
        raw = await self.rpc.call("getKey", [hex_bytes(key_id, 32)], block)
        if raw is None:
            return None
        result = self._key(key_id, raw, block)
        await self.rpc.check(block)
        return result

    @dependency_boundary
    async def document(self, document_id: str, version: int | None) -> WalletDocument | None:
        block = await self.rpc.snapshot()
        identifier = hex_bytes(document_id, 32)
        latest = (await self.rpc.call("latestVersion", [identifier], block))[0]
        require(type(latest) is int and latest >= 0, "invalid latest version")
        if version is None:
            if latest == 0:
                return None
            version = latest
        require(type(version) is int and version > 0, "invalid requested version")
        raw = await self.rpc.call("getDocument", [identifier, version], block)
        if raw is None:
            require(version > latest, "known document version missing")
            return None
        doc = named(self.rpc.functions["getDocument"]["outputs"][0]["components"], raw[0])
        require(
            calculate_document_id(doc["issuerId"], doc["docKey"]) == document_id
            and doc["version"] == version
            and version <= latest,
            "document identity mismatch",
        )
        state = {1: "ACTIVE", 2: "REVOKED", 3: "SUPERSEDED"}[doc["state"]]
        require(
            (state != "ACTIVE" or version == latest)
            and (state != "SUPERSEDED" or version < latest),
            "invalid state/latest",
        )
        require(
            0 < doc["publishedBlock"] <= quantity(block["number"])
            and doc["publishedAt"] <= quantity(block["timestamp"])
            and doc["issuedAt"] < doc["expiresAt"],
            "invalid publication position/time",
        )
        issuer = await self.rpc.call("getIssuer", [hex_bytes(doc["issuerId"], 32)], block)
        raw_key = await self.rpc.call("getKey", [hex_bytes(doc["keyId"], 32)], block)
        require(
            issuer is not None and issuer[0] in (1, 2) and raw_key is not None,
            "document issuer/key absent",
        )
        key = self._key(doc["keyId"], raw_key, block)
        require(
            key.issuer_id == doc["issuerId"]
            and int(key.registered_block) <= doc["publishedBlock"]
            and (key.retired_block is None or int(key.retired_block) >= doc["publishedBlock"]),
            "document key history mismatch",
        )
        warnings = []
        if issuer[0] == 2:
            warnings.append("ISSUER_SUSPENDED")
        if key.compromise_block is not None:
            warnings.append("KEY_COMPROMISED")
        if state == "ACTIVE" and quantity(block["timestamp"]) >= doc["expiresAt"]:
            state = "EXPIRED"
        await self.rpc.check(block)
        return WalletDocument(
            **self._position(block),
            published_at=doc["publishedAt"],
            published_block=str(doc["publishedBlock"]),
            document=DocumentView(
                document_id=document_id,
                issuer_id=doc["issuerId"],
                doc_key=doc["docKey"],
                key_id=doc["keyId"],
                version=version,
                latest_version=latest,
                state=state,
                warnings=warnings,
                original_hash=doc["originalHash"],
                protected_hash=doc["protectedHash"],
                content_schema=doc["contentSchema"],
                issued_at=doc["issuedAt"],
                expires_at=doc["expiresAt"],
                original_available=False,
            ),
        )

    @dependency_boundary
    async def proposal(self, proposal_id: str) -> WalletProposal | None:
        hex_bytes(proposal_id, 32)
        evidence = await self.reconciler.proposal(proposal_id)
        if evidence is None:
            return None
        block = evidence["block"]
        fields = self.rpc.functions["getProposal"]["outputs"][0]["components"]
        proposal = GovernanceProposal.model_validate(port_arguments(fields, evidence["proposal"]))
        nonce = (
            await self.rpc.call("governanceNonce", [hex_bytes(proposal.issuer_id, 32)], block)
        )[0]
        require(nonce >= int(proposal.nonce), "governance nonce regressed")
        if evidence["executed"]:
            require(nonce > int(proposal.nonce), "execution nonce not consumed")
            status = "EXECUTED"
        elif quantity(block["timestamp"]) >= proposal.deadline:
            status = "EXPIRED"
        elif nonce != int(proposal.nonce):
            status = "STALE"
        else:
            status = "PENDING"
        await self.rpc.check(block)
        return WalletProposal(
            **self._position(block),
            proposal=ProposalView(
                proposal_id=proposal_id,
                proposal=proposal,
                status=status,
                approvals=evidence["approvals"],
            ),
        )

    @dependency_boundary
    async def transaction(self, tx_hash: str) -> WalletTransaction | None:
        hex_bytes(tx_hash, 32)
        actual = await self.rpc.transaction_evidence(tx_hash)
        if actual is None:
            return None
        evidence = await self.reconciler.transaction(
            tx_hash,
            function=actual["function"],
            arguments=actual["arguments"],
            sender=actual["sender"],
        )
        if evidence is None:
            return None
        actions = {
            "publish": "Publish",
            "revoke": "Revoke",
            "propose": "Propose",
            "approve": "Approve",
            "suspendIssuer": "Suspend",
        }
        return WalletTransaction(
            chain_id=str(self.rpc.chain_id),
            verifying_contract=self.rpc.address,
            tx_hash=tx_hash,
            sender=evidence["sender"],
            action=actions[evidence["function"]],
            arguments=port_arguments(
                self.rpc.functions[evidence["function"]]["inputs"], evidence["arguments"]
            ),
            status="CONFIRMED" if evidence["receipt_status"] == 1 else "FAILED",
            block_number=str(quantity(evidence["block"]["number"])),
            block_hash=evidence["block"]["hash"],
        )

    async def is_approver(self, address: str) -> bool:
        raise DependencyUnavailableError(
            "verified approver deployment provenance is not configured"
        )

    async def submit(self, request: SigningRequest, signature: str) -> str | None:
        raise DependencyUnavailableError("read-only adapter: relayer submission is not configured")

    async def find_transaction(self, intent: dict) -> WalletTransaction | None:
        raise DependencyUnavailableError(
            "C recovery pagination/persistence contract is not connected"
        )
