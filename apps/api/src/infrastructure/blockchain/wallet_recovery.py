"""Bounded, read-only recovery of the original wallet intent. Never authorizes resend."""

from eth_abi import encode
from eth_utils import keccak, to_normalized_address

from .errors import BlockchainConfigurationError, BlockchainDependencyError
from .wallet_reconciliation import WalletReconciler, require
from .wallet_rpc import abi_type, hex_bytes, quantity, signature


def calldata(rpc, function, arguments):
    def values(fields, data):
        if not isinstance(data, dict) or set(data) != {x["name"] for x in fields}:
            raise ValueError("complete ABI arguments required")
        result = []
        for field in fields:
            value = data[field["name"]]
            if field["type"] == "tuple":
                value = tuple(values(field["components"], value))
            elif field["type"] in {"bytes", "bytes32"}:
                value = hex_bytes(value, 32 if field["type"] == "bytes32" else None)
            result.append(value)
        return result

    try:
        entry = rpc.functions[function]
        return keccak(text=signature(entry))[:4] + encode(
            [abi_type(x) for x in entry["inputs"]],
            values(entry["inputs"], arguments),
        )
    except Exception as exc:
        raise BlockchainConfigurationError("invalid complete wallet intent") from exc


class WalletRecovery:
    def __init__(self, rpc):
        self.rpc, self.reconciler = rpc, WalletReconciler(rpc)

    async def find_transaction(
        self,
        *,
        function,
        arguments,
        start_block,
        sender=None,
        known_tx_hash=None,
        max_blocks=128,
        max_transactions=4096,
        previous_checkpoint=None,
    ):
        if (
            function not in {"publish", "revoke", "propose", "approve", "suspendIssuer"}
            or type(start_block) is not int
            or start_block < self.rpc.deployment_block
            or type(max_blocks) is not int
            or not 1 <= max_blocks <= 1024
            or type(max_transactions) is not int
            or not 1 <= max_transactions <= 16384
        ):
            raise BlockchainConfigurationError("invalid bounded wallet search")
        if function in {"propose", "approve", "suspendIssuer"} and sender is None:
            raise BlockchainConfigurationError("stored governance sender is required")
        expected = calldata(self.rpc, function, arguments)
        head = await self.rpc.snapshot()
        if previous_checkpoint is not None:
            try:
                number, block_hash = previous_checkpoint
                hex_bytes(block_hash, 32)
                if type(number) is not int:
                    raise ValueError("checkpoint height must be integer")
            except (TypeError, ValueError) as exc:
                raise BlockchainConfigurationError("invalid search checkpoint") from exc
            if start_block != number + 1 or number < self.rpc.deployment_block:
                raise BlockchainConfigurationError("search checkpoint does not precede range")
            require(
                (await self.rpc.block(hex(number)))["hash"] == block_hash,
                "search checkpoint reorg; keep UNKNOWN and restart canonical search",
            )
        attempts, seen = [], {}

        async def collect(tx_hash):
            evidence = await self.reconciler.transaction(
                tx_hash,
                function=function,
                arguments=arguments,
                sender=sender,
            )
            if evidence is not None:
                require(
                    quantity(evidence["block"]["number"]) <= quantity(head["number"]),
                    "candidate mined after search snapshot; retry",
                )
                attempts.append({"tx_hash": tx_hash, "evidence": evidence})
                seen[tx_hash] = evidence["block"]
            return evidence

        if known_tx_hash is not None:
            try:
                hex_bytes(known_tx_hash, 32)
            except (TypeError, ValueError) as exc:
                raise BlockchainConfigurationError("invalid known transaction hash") from exc
            await collect(known_tx_hash)
        end_number = min(start_block + max_blocks - 1, quantity(head["number"]))
        end, examined = None, 0
        try:
            for number in range(start_block, end_number + 1):
                block = await self.rpc.block(hex(number))
                hashes = block["transactions"]
                if not isinstance(hashes, list) or len(set(hashes)) != len(hashes):
                    raise ValueError("invalid block transaction list")
                examined += len(hashes)
                require(examined <= max_transactions, "search transaction budget exceeded")
                for index, tx_hash in enumerate(hashes):
                    hex_bytes(tx_hash, 32)
                    if tx_hash in seen:
                        require(
                            seen[tx_hash]["hash"] == block["hash"]
                            and seen[tx_hash]["number"] == block["number"],
                            "duplicate transaction across canonical blocks",
                        )
                        continue
                    tx = await self.rpc.rpc("eth_getTransactionByHash", [tx_hash])
                    require(
                        isinstance(tx, dict)
                        and tx["hash"] == tx_hash
                        and tx["blockHash"] == block["hash"]
                        and tx["blockNumber"] == block["number"]
                        and quantity(tx["transactionIndex"]) == index,
                        "inconsistent canonical search transaction",
                    )
                    target = None if tx["to"] is None else to_normalized_address(tx["to"])
                    if target != self.rpc.address or hex_bytes(tx["input"]) != expected:
                        continue
                    if sender is not None and to_normalized_address(tx["from"]) != sender:
                        continue
                    require(
                        await collect(tx_hash) is not None,
                        "mined candidate receipt unavailable; keep UNKNOWN",
                    )
                end = block
            await self.rpc.check(head)
            if end is not None:
                await self.rpc.check(end)
        except (KeyError, TypeError, ValueError) as exc:
            raise BlockchainDependencyError("invalid wallet search observation") from exc
        nonce = None
        if function in {"publish", "revoke"}:
            nonce = (
                await self.rpc.call(
                    "nextNonce",
                    [
                        hex_bytes(
                            arguments["message"]["issuerId"],
                            32,
                        )
                    ],
                    head,
                )
            )[0]
        await self.rpc.check(head)
        return {
            "attempts": attempts,
            "head": head,
            "scanned_from": start_block,
            "scanned_to": None if end is None else end_number,
            "checkpoint": None if end is None else (end_number, end["hash"]),
            "next_block": start_block if end is None else end_number + 1,
            "reached_snapshot": end is not None and end_number == quantity(head["number"]),
            "observed_next_nonce": nonce,
        }
