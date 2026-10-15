"""C/B runtime boundary; an unavailable Registry never becomes a successful mock."""

from typing import Literal, Protocol

from pydantic import model_validator

from .wallet_contract import (
    Address,
    ContractModel,
    DocumentView,
    Hex32,
    ProposalView,
    Seconds,
    SigningRequest,
    Uint256,
)


class ChainPosition(ContractModel):
    chain_id: Uint256
    verifying_contract: Address
    block_number: Uint256
    block_hash: Hex32


class WalletIssuer(ChainPosition):
    issuer_id: Hex32
    state: Literal["ACTIVE", "SUSPENDED"]
    key_id: Hex32
    signer: Address
    metadata_hash: Hex32
    next_nonce: Uint256
    governance_nonce: Uint256


class WalletKey(ChainPosition):
    key_id: Hex32
    issuer_id: Hex32
    signer: Address
    registered_block: Uint256
    retired_block: Uint256 | None = None
    compromise_block: Uint256 | None = None


class WalletDocument(ChainPosition):
    document: DocumentView
    published_at: Seconds
    published_block: Uint256


class WalletProposal(ChainPosition):
    proposal: ProposalView

    @model_validator(mode="after")
    def distinct_approvals(self):
        approvals = self.proposal.approvals
        if len(set(approvals)) != len(approvals) or len(approvals) > 3:
            raise ValueError("invalid approver set")
        if (self.proposal.status == "EXECUTED") != (len(approvals) >= 2):
            raise ValueError("execution requires two distinct approvals")
        return self


class WalletTransaction(ContractModel):
    chain_id: Uint256
    verifying_contract: Address
    tx_hash: Hex32
    sender: Address
    action: Literal["Publish", "Revoke", "Propose", "Approve", "Suspend"]
    arguments: dict
    status: Literal["SUBMITTED", "CONFIRMED", "FAILED", "UNKNOWN"]
    block_number: Uint256 | None = None
    block_hash: Hex32 | None = None

    @model_validator(mode="after")
    def confirmed_position(self):
        if self.status == "CONFIRMED" and (self.block_number is None or self.block_hash is None):
            raise ValueError("confirmation requires canonical receipt and event/state checks")
        return self


class WalletRegistry(Protocol):
    """B decodes ABI, verifies deployment/canonical blocks, receipt, events and current state.

    Returned arguments are decoded actual calldata, never an echo of the requested intent.
    find_transaction searches the original intent/nonce and never sends a new transaction.
    C independently compares chain, contract, action, signer and immutable arguments.
    """

    async def issuer(self, issuer_id: str) -> WalletIssuer | None: ...

    async def key(self, key_id: str) -> WalletKey | None: ...

    async def document(self, document_id: str, version: int | None) -> WalletDocument | None: ...

    async def proposal(self, proposal_id: str) -> WalletProposal | None: ...

    async def is_approver(self, address: str) -> bool: ...

    async def transaction(self, tx_hash: str) -> WalletTransaction | None: ...

    async def submit(self, request: SigningRequest, signature: str) -> str | None: ...

    async def find_transaction(self, intent: dict) -> WalletTransaction | None: ...
