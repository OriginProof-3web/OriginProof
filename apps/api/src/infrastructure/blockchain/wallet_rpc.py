"""B's ABI evidence boundary. C owns conversion to wallet_ports runtime models.

All observations use a hash-pinned canonical block. Projection is never read here.
The supplied ABI is the compiled Registry ABI, not a second contract definition.
"""

from itertools import count

import httpx
from eth_abi import decode, encode
from eth_abi.exceptions import DecodingError
from eth_utils import keccak, to_normalized_address

from .errors import BlockchainConfigurationError, BlockchainDependencyError


def abi_type(field):
    if field["type"] == "tuple":
        return "(" + ",".join(abi_type(item) for item in field["components"]) + ")"
    return field["type"]


def signature(entry):
    return entry["name"] + "(" + ",".join(abi_type(x) for x in entry["inputs"]) + ")"


def hex_bytes(value, size=None):
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("invalid hex")
    raw = bytes.fromhex(value[2:])
    if size is not None and len(raw) != size:
        raise ValueError("invalid hex length")
    return raw


def quantity(value):
    if not isinstance(value, str) or not value.startswith("0x"):
        raise ValueError("invalid RPC quantity")
    result = int(value, 16)
    if result < 0 or value != hex(result):
        raise ValueError("noncanonical RPC quantity")
    return result


def named(fields, values):
    result = {}
    for field, value in zip(fields, values, strict=True):
        if field["type"] == "tuple":
            value = named(field["components"], value)
        elif isinstance(value, bytes):
            value = "0x" + value.hex()
        result[field["name"]] = value
    return result


class _CallReverted(BlockchainDependencyError):
    def __init__(self, data):
        super().__init__("wallet eth_call reverted")
        self.data = data


class WalletRpc:
    def __init__(self, client: httpx.AsyncClient, rpc_url, *, chain_id, address,
                 deployment_block, deployment_hash, runtime_code_hash, abi):
        try:
            self.address = to_normalized_address(address)
            if int(self.address, 16) == 0 or chain_id <= 0 or deployment_block < 0:
                raise ValueError("invalid deployment")
            hex_bytes(deployment_hash, 32)
            hex_bytes(runtime_code_hash, 32)
        except (TypeError, ValueError) as exc:
            raise BlockchainConfigurationError("invalid wallet deployment") from exc
        self.client, self.url = client, rpc_url
        self.chain_id = chain_id
        self.deployment_block, self.deployment_hash = deployment_block, deployment_hash
        self.runtime_code_hash = runtime_code_hash
        self.functions = {x["name"]: x for x in abi if x["type"] == "function"}
        self.selectors = {keccak(text=signature(x))[:4]: x for x in self.functions.values()}
        self.events = {
            "0x" + keccak(text=signature(x)).hex(): x for x in abi if x["type"] == "event"
        }
        self.abi_errors = [x for x in abi if x["type"] == "error"]
        self.ids = count(1)

    async def rpc(self, method, params):
        request_id = next(self.ids)
        try:
            response = await self.client.post(self.url, json={
                "jsonrpc": "2.0", "id": request_id, "method": method, "params": params,
            })
            response.raise_for_status()
            body = response.json()
            if (not isinstance(body, dict) or body.get("jsonrpc") != "2.0"
                    or body.get("id") != request_id
                    or ("error" in body) == ("result" in body)):
                raise ValueError("invalid RPC envelope")
            if "error" in body:
                error = body["error"]
                if method == "eth_call" and isinstance(error, dict):
                    data = hex_bytes(error.get("data"))
                    raise _CallReverted(data)
                raise ValueError("RPC error")
            return body["result"]
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise BlockchainDependencyError("wallet RPC unavailable or invalid response") from exc

    async def block(self, number):
        result = await self.rpc("eth_getBlockByNumber", [number, False])
        try:
            quantity(result["number"])
            hex_bytes(result["hash"], 32)
            quantity(result["timestamp"])
            if number != "latest" and result["number"] != number:
                raise ValueError("wrong block")
            return result
        except (KeyError, TypeError, ValueError) as exc:
            raise BlockchainDependencyError("invalid canonical block") from exc

    async def snapshot(self):
        try:
            if quantity(await self.rpc("eth_chainId", [])) != self.chain_id:
                raise ValueError("wrong chain")
            deployment = await self.block(hex(self.deployment_block))
            if deployment["hash"] != self.deployment_hash:
                raise ValueError("deployment changed")
            head = await self.block("latest")
            if quantity(head["number"]) < self.deployment_block:
                raise ValueError("chain predates deployment")
            code = hex_bytes(await self.rpc("eth_getCode", [self.address, self.pin(head)]))
            if not code or "0x" + keccak(code).hex() != self.runtime_code_hash:
                raise ValueError("runtime code mismatch")
            await self.check(head)
            return head
        except (TypeError, ValueError) as exc:
            raise BlockchainDependencyError("wallet deployment mismatch") from exc

    @staticmethod
    def pin(block):
        return {"blockHash": block["hash"], "requireCanonical": True}

    async def check(self, block):
        current = await self.block(block["number"])
        if current["hash"] != block["hash"]:
            raise BlockchainDependencyError("canonical block changed; retry observation")

    async def read(self, name, args):
        """Deployment-verified current observation, independent of projection lag."""
        block = await self.snapshot()
        result = await self.call(name, args, block)
        return {"block": block, "values": result}

    async def call(self, name, args, block):
        entry = self.functions[name]
        if entry.get("stateMutability") not in ("view", "pure"):
            raise BlockchainConfigurationError("read requires a view function")
        data = keccak(text=signature(entry))[:4] + encode(
            [abi_type(x) for x in entry["inputs"]], args,
        )
        try:
            raw = await self.rpc("eth_call", [{"to": self.address, "data": "0x" + data.hex()},
                                              self.pin(block)])
        except _CallReverted as exc:
            missing = {"getIssuer": "UnknownIssuer", "getKey": "UnknownKey",
                       "getProposal": "UnknownProposal", "getDocument": "UnknownDocument"}
            error = next((x for x in self.abi_errors if x["name"] == missing.get(name)), None)
            if error is None or exc.data != keccak(text=signature(error))[:4]:
                raise
            await self.check(block)
            return None
        try:
            types = [abi_type(x) for x in entry["outputs"]]
            decoded = decode(types, hex_bytes(raw))
            if encode(types, decoded) != hex_bytes(raw):
                raise ValueError("noncanonical ABI result")
        except Exception as exc:
            raise BlockchainDependencyError("invalid wallet ABI result") from exc
        await self.check(block)
        return decoded

    def decode_log(self, log):
        try:
            if (to_normalized_address(log["address"]) != self.address
                    or log.get("removed", False)):
                raise ValueError("wrong contract or removed log")
            entry = self.events[log["topics"][0]]
            indexed = [x for x in entry["inputs"] if x["indexed"]]
            plain = [x for x in entry["inputs"] if not x["indexed"]]
            if len(log["topics"]) != len(indexed) + 1:
                raise ValueError("wrong topic count")
            indexed_values = [decode([abi_type(x)], hex_bytes(topic, 32))[0]
                              for x, topic in zip(indexed, log["topics"][1:], strict=True)]
            raw = hex_bytes(log["data"])
            types = [abi_type(x) for x in plain]
            values = decode(types, raw)
            if encode(types, values) != raw:
                raise ValueError("noncanonical event")
            hex_bytes(log["blockHash"], 32)
            hex_bytes(log["transactionHash"], 32)
            quantity(log["blockNumber"])
            quantity(log["logIndex"])
            return {"name": entry["name"], "arguments": {
                **named(indexed, indexed_values), **named(plain, values),
            }}
        except Exception as exc:
            raise BlockchainDependencyError("invalid wallet event") from exc

    async def logs(self, start, block):
        if not self.deployment_block <= start <= quantity(block["number"]):
            raise BlockchainConfigurationError("invalid event range")
        raw = await self.rpc("eth_getLogs", [{
            "address": self.address, "fromBlock": hex(start), "toBlock": block["number"],
        }])
        try:
            if not isinstance(raw, list):
                raise ValueError("invalid log list")
            result, seen, blocks = [], set(), {}
            for log in raw:
                decoded = self.decode_log(log)
                number = quantity(log["blockNumber"])
                position = (number, quantity(log["logIndex"]))
                if not start <= number <= quantity(block["number"]) or position in seen:
                    raise ValueError("event range or duplicate")
                seen.add(position)
                if number not in blocks:
                    blocks[number] = await self.block(hex(number))
                if blocks[number]["hash"] != log["blockHash"]:
                    raise ValueError("orphan log")
                result.append({**log, "decoded": decoded})
            await self.check(block)
            return sorted(result, key=lambda x: (quantity(x["blockNumber"]),
                                                quantity(x["logIndex"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise BlockchainDependencyError("invalid canonical wallet logs") from exc

    async def transaction_evidence(self, tx_hash):
        """Return actual calldata/receipt evidence, never an echoed intent or confirmation.

        C's CONFIRMED needs action-specific event/state reconciliation on top of this.
        Missing/pending receipts return None; this method never sends a transaction.
        """
        try:
            hex_bytes(tx_hash, 32)
            head = await self.snapshot()
            tx = await self.rpc("eth_getTransactionByHash", [tx_hash])
            receipt = await self.rpc("eth_getTransactionReceipt", [tx_hash])
            if tx is None or receipt is None:
                return None
            if (tx["hash"] != tx_hash or receipt["transactionHash"] != tx_hash
                    or to_normalized_address(tx["to"]) != self.address
                    or to_normalized_address(receipt["to"]) != self.address
                    or to_normalized_address(tx["from"]) !=
                    to_normalized_address(receipt["from"])):
                raise ValueError("transaction identity mismatch")
            if quantity(tx["chainId"]) != self.chain_id or quantity(tx["value"]) != 0:
                raise ValueError("wrong transaction domain")
            number = quantity(receipt["blockNumber"])
            if not self.deployment_block <= number <= quantity(head["number"]):
                raise ValueError("transaction outside deployment")
            block = await self.block(receipt["blockNumber"])
            if (block["hash"] != receipt["blockHash"] or tx["blockHash"] != block["hash"]
                    or tx["blockNumber"] != block["number"]
                    or tx["transactionIndex"] != receipt["transactionIndex"]):
                raise ValueError("orphan receipt")
            index = quantity(receipt["transactionIndex"])
            if index >= len(block["transactions"]) or block["transactions"][index] != tx_hash:
                raise ValueError("transaction not included at canonical receipt position")
            raw = hex_bytes(tx["input"])
            entry = self.selectors[raw[:4]]
            if entry.get("stateMutability") != "nonpayable":
                raise ValueError("not a wallet mutation")
            types = [abi_type(x) for x in entry["inputs"]]
            args = decode(types, raw[4:])
            if encode(types, args) != raw[4:]:
                raise ValueError("noncanonical calldata")
            status = quantity(receipt["status"])
            if status not in (0, 1) or (status == 0 and receipt["logs"]):
                raise ValueError("invalid receipt status/logs")
            events, positions = [], set()
            for log in receipt["logs"]:
                if (log["transactionHash"] != tx_hash or log["blockHash"] != block["hash"]
                        or log["blockNumber"] != block["number"]):
                    raise ValueError("receipt log identity mismatch")
                position = quantity(log["logIndex"])
                if position in positions:
                    raise ValueError("duplicate receipt log")
                positions.add(position)
                events.append(self.decode_log(log))
            await self.check(block)
            await self.check(head)
            return {"function": entry["name"], "arguments": named(entry["inputs"], args),
                    "sender": to_normalized_address(tx["from"]), "receipt_status": status,
                    "block": block, "events": events}
        except (KeyError, TypeError, ValueError, DecodingError) as exc:
            raise BlockchainDependencyError("invalid wallet transaction evidence") from exc
