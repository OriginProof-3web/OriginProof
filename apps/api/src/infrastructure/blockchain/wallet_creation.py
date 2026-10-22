"""Verify top-level CREATE provenance before deriving immutable Registry approvers."""

from dataclasses import dataclass

from eth_abi import decode, encode
from eth_abi.exceptions import DecodingError
from eth_utils import keccak
from originproof_core.wallet_contract import Address
from pydantic import TypeAdapter

from .errors import BlockchainConfigurationError, BlockchainDependencyError
from .wallet_reconciliation import require
from .wallet_rpc import abi_type, hex_bytes, quantity

ADDRESS = TypeAdapter(Address)


@dataclass(frozen=True)
class WalletCreationProof:
    """Trusted build bytecode + deployment reference, never a user-supplied address list."""

    tx_hash: str
    creation_bytecode: bytes

    def __post_init__(self):
        try:
            hex_bytes(self.tx_hash, 32)
            if (
                self.tx_hash != self.tx_hash.lower()
                or type(self.creation_bytecode) is not bytes
                or not self.creation_bytecode
            ):
                raise ValueError("invalid creation proof")
        except (TypeError, ValueError) as exc:
            raise BlockchainConfigurationError("invalid wallet creation proof") from exc


async def verified_approvers(rpc, proof: WalletCreationProof):
    """No cached authorization: recheck canonical creation and code on every call."""
    try:
        head = await rpc.snapshot()
        block = await rpc.block(hex(rpc.deployment_block))
        tx = await rpc.rpc("eth_getTransactionByHash", [proof.tx_hash])
        receipt = await rpc.rpc("eth_getTransactionReceipt", [proof.tx_hash])
        require(isinstance(tx, dict) and isinstance(receipt, dict), "creation evidence missing")
        require(tx["hash"] == receipt["transactionHash"] == proof.tx_hash, "creation hash mismatch")
        require(tx["to"] is None and receipt["to"] is None, "top-level CREATE required")
        require(
            ADDRESS.validate_python(receipt["contractAddress"]) == rpc.address,
            "wrong created contract",
        )
        require(
            ADDRESS.validate_python(tx["from"]) == ADDRESS.validate_python(receipt["from"]),
            "creation sender mismatch",
        )
        require(
            quantity(tx["chainId"]) == rpc.chain_id and quantity(tx["value"]) == 0,
            "wrong creation domain/value",
        )
        require(
            tx["blockHash"] == receipt["blockHash"] == block["hash"] == rpc.deployment_hash
            and tx["blockNumber"] == receipt["blockNumber"] == block["number"],
            "creation deployment mismatch",
        )
        index = quantity(tx["transactionIndex"])
        require(
            index == quantity(receipt["transactionIndex"])
            and isinstance(block["transactions"], list)
            and index < len(block["transactions"])
            and block["transactions"][index] == proof.tx_hash,
            "creation not in canonical block position",
        )
        require(quantity(receipt["status"]) == 1, "creation receipt failed")
        constructor = rpc.constructor
        require(
            constructor is not None and constructor["stateMutability"] == "nonpayable",
            "constructor ABI missing or inconsistent",
        )
        types = [abi_type(field) for field in constructor["inputs"]]
        require(types == ["address[3]"], "unexpected Registry constructor ABI")
        creation = hex_bytes(tx["input"])
        prefix = proof.creation_bytecode
        require(creation.startswith(prefix), "untrusted creation bytecode")
        arguments = creation[len(prefix) :]
        decoded = decode(types, arguments)
        require(encode(types, decoded) == arguments, "noncanonical constructor arguments")
        approvers = tuple(ADDRESS.validate_python(address) for address in decoded[0])
        require(len(approvers) == 3 and len(set(approvers)) == 3, "invalid fixed approver set")
        code = hex_bytes(await rpc.rpc("eth_getCode", [rpc.address, rpc.pin(block)]))
        require(
            bool(code) and "0x" + keccak(code).hex() == rpc.runtime_code_hash,
            "deployment runtime code mismatch",
        )
        await rpc.check(block)
        await rpc.check(head)
        return approvers
    except (KeyError, TypeError, ValueError, DecodingError) as exc:
        raise BlockchainDependencyError("invalid wallet creation evidence") from exc
