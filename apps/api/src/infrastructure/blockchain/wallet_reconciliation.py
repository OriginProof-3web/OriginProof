"""Reconcile B's ABI evidence without copying C's runtime port/models."""

import json

from eth_abi import encode
from eth_utils import keccak

from .errors import BlockchainConfigurationError, BlockchainDependencyError
from .wallet_rpc import abi_type, hex_bytes, named, quantity


def require(condition, message):
    if not condition:
        raise BlockchainDependencyError(message)


class WalletReconciler:
    def __init__(self, rpc):
        self.rpc = rpc

    async def proposal(self, proposal_id):
        block = await self.rpc.snapshot()
        return await self._proposal_at(proposal_id, block)

    async def _proposal_at(self, proposal_id, block):
        raw = await self.rpc.call("getProposal", [hex_bytes(proposal_id, 32)], block)
        if raw is None:
            return None
        value, count, executed = raw
        field = self.rpc.functions["getProposal"]["outputs"][0]
        calculated = keccak(
            encode(
                ["uint256", "address", abi_type(field)],
                [self.rpc.chain_id, self.rpc.address, value],
            )
        )
        require(calculated == hex_bytes(proposal_id, 32), "proposal ID/tuple mismatch")
        proposal = named(field["components"], value)
        logs = await self.rpc.logs(self.rpc.deployment_block, block)
        approvals, created, execution, last_approval = [], None, None, None
        for log in logs:
            event = log["decoded"]
            args, name = event["arguments"], event["name"]
            if args.get("proposalId") != proposal_id:
                continue
            if name == "ProposalCreated":
                require(
                    created is None and not approvals, "duplicate/out-of-order proposal creation"
                )
                require(
                    args["issuerId"] == proposal["issuerId"]
                    and args["action"] == proposal["action"],
                    "proposal creation mismatch",
                )
                created = log
            elif name == "ProposalApproved":
                actor = args["approver"]
                require(created is not None and execution is None, "approval outside proposal")
                require(
                    int(actor, 16) != 0 and actor not in approvals and len(approvals) < 2,
                    "invalid distinct approval set",
                )
                approvals.append(actor)
                require(args["count"] == len(approvals), "approval event count mismatch")
                last_approval = log
            elif name == "ProposalExecuted":
                require(
                    created is not None and len(approvals) == 2 and execution is None,
                    "execution without two distinct approvals",
                )
                require(
                    args["issuerId"] == proposal["issuerId"]
                    and args["action"] == proposal["action"],
                    "proposal execution mismatch",
                )
                require(
                    log["transactionHash"] == last_approval["transactionHash"],
                    "execution not atomic with second approval",
                )
                execution = log
        require(
            created is not None
            and count == len(approvals)
            and executed == (execution is not None)
            and executed == (len(approvals) == 2),
            "proposal state/event mismatch",
        )
        await self.rpc.check(block)
        return {"block": block, "proposal": proposal, "approvals": approvals, "executed": executed}

    async def transaction(self, tx_hash, *, function, arguments, sender=None):
        """Match the complete stored intent; return evidence, not C's WalletTransaction.

        Later revocation, supersession and suspension remain visible in current_state.
        An ambiguous receipt-block suspension is rejected rather than inferred from latest.
        """
        if function not in {"publish", "revoke", "propose", "approve", "suspendIssuer"}:
            raise BlockchainConfigurationError("unsupported wallet mutation")
        if function in {"propose", "approve", "suspendIssuer"} and sender is None:
            raise BlockchainConfigurationError("stored governance sender is required")
        evidence = await self.rpc.transaction_evidence(tx_hash)
        if evidence is None:
            return None
        require(
            evidence["function"] == function
            and json.dumps(evidence["arguments"], sort_keys=True, allow_nan=False)
            == json.dumps(arguments, sort_keys=True, allow_nan=False),
            "transaction does not match complete stored intent",
        )
        require(sender is None or evidence["sender"] == sender, "transaction sender mismatch")
        if evidence["receipt_status"] == 0:
            return evidence
        receipt, current = evidence["block"], await self.rpc.snapshot()
        require(
            quantity(current["number"]) >= quantity(receipt["number"]),
            "current head predates receipt",
        )
        if function in {"publish", "revoke"}:
            old, latest = await self._document_transaction(evidence, receipt, current)
        elif function in {"propose", "approve"}:
            old, latest = await self._proposal_transaction(evidence, receipt, current)
        else:
            old, latest = await self._suspension(evidence, receipt, current)
        await self.rpc.check(receipt)
        await self.rpc.check(current)
        return {**evidence, "receipt_state": old, "current_state": latest, "current_block": current}

    def _events(self, evidence, expected):
        require(evidence["events"] == expected, "transaction event sequence/arguments mismatch")

    async def _document_at(self, message, block):
        doc_id = hex_bytes(message["documentId"], 32)
        result = await self.rpc.call("getDocument", [doc_id, message["version"]], block)
        require(result is not None, "document absent after successful mutation")
        field = self.rpc.functions["getDocument"]["outputs"][0]
        doc = named(field["components"], result[0])
        latest = (await self.rpc.call("latestVersion", [doc_id], block))[0]
        require(
            all(doc[x] == message[x] for x in ("issuerId", "docKey", "version")),
            "document ownership/version mismatch",
        )
        require(
            doc["state"] in (1, 2, 3)
            and latest >= doc["version"]
            and (doc["state"] != 1 or latest == doc["version"])
            and (doc["state"] != 3 or latest > doc["version"]),
            "invalid document state/latest",
        )
        require(
            0 < doc["publishedBlock"] <= quantity(block["number"])
            and doc["publishedAt"] <= quantity(block["timestamp"]),
            "invalid publication position",
        )
        nonce = (await self.rpc.call("nextNonce", [hex_bytes(message["issuerId"], 32)], block))[0]
        require(nonce > message["nonce"], "business nonce not consumed")
        issuer = await self.rpc.call("getIssuer", [hex_bytes(doc["issuerId"], 32)], block)
        key = await self.rpc.call("getKey", [hex_bytes(doc["keyId"], 32)], block)
        require(
            issuer is not None and issuer[0] in (1, 2) and key is not None,
            "document issuer/key history absent",
        )
        require(
            key[0][0] == hex_bytes(doc["issuerId"], 32) and 0 < key[0][2] <= doc["publishedBlock"],
            "document key history mismatch",
        )
        return {
            "document": doc,
            "latest_version": latest,
            "next_nonce": nonce,
            "issuer": issuer,
            "publication_key": key[0],
        }

    async def _document_transaction(self, evidence, receipt, current):
        function, message = evidence["function"], evidence["arguments"]["message"]
        require(message["action"] == (1 if function == "publish" else 2), "wrong signed action")
        require(
            keccak(
                encode(
                    ["bytes32", "bytes32"],
                    [hex_bytes(message["issuerId"], 32), hex_bytes(message["docKey"], 32)],
                )
            )
            == hex_bytes(message["documentId"], 32),
            "document ID mismatch",
        )
        identity = {x: message[x] for x in ("documentId", "version", "issuerId")}
        expected = [
            {
                "name": "DocumentPublished" if function == "publish" else "DocumentRevoked",
                "arguments": identity,
            }
        ]
        if function == "publish" and message["version"] > 1:
            expected.insert(
                0,
                {
                    "name": "DocumentSuperseded",
                    "arguments": {
                        "documentId": message["documentId"],
                        "version": message["version"] - 1,
                        "replacement": message["version"],
                    },
                },
            )
        self._events(evidence, expected)
        old = await self._document_at(message, receipt)
        latest = await self._document_at(message, current)
        immutable = set(old["document"]) - {"state"}
        require(
            all(old["document"][x] == latest["document"][x] for x in immutable)
            and latest["latest_version"] >= old["latest_version"]
            and latest["next_nonce"] >= old["next_nonce"],
            "document history regressed",
        )
        require(
            old["document"]["state"] == 1 or latest["document"]["state"] != 1,
            "document state resurrected",
        )
        if function == "publish":
            require(
                all(
                    old["document"][x] == message[x]
                    for x in (
                        "keyId",
                        "originalHash",
                        "protectedHash",
                        "contentSchema",
                        "issuedAt",
                        "expiresAt",
                    )
                ),
                "published immutable fields mismatch",
            )
            require(
                old["document"]["publishedBlock"] == quantity(receipt["number"])
                and old["document"]["publishedAt"] == quantity(receipt["timestamp"]),
                "publication receipt position mismatch",
            )
        else:
            # publish only supersedes ACTIVE versions, so a revoked version stays REVOKED.
            require(
                old["document"]["state"] == 2 and latest["document"]["state"] == 2,
                "revocation missing or resurrected",
            )
        return old, latest

    async def _proposal_transaction(self, evidence, receipt, current):
        args = evidence["arguments"]
        if evidence["function"] == "propose":
            field = self.rpc.functions["propose"]["inputs"][0]
            proposal = args["proposal"]
            values = [proposal[x["name"]] for x in field["components"]]
            values = [
                hex_bytes(v, 32) if x["type"] == "bytes32" else v
                for x, v in zip(field["components"], values, strict=True)
            ]
            proposal_id = (
                "0x"
                + keccak(
                    encode(
                        ["uint256", "address", abi_type(field)],
                        [self.rpc.chain_id, self.rpc.address, tuple(values)],
                    )
                ).hex()
            )
            self._events(
                evidence,
                [
                    {
                        "name": "ProposalCreated",
                        "arguments": {
                            "proposalId": proposal_id,
                            "issuerId": proposal["issuerId"],
                            "action": proposal["action"],
                        },
                    }
                ],
            )
        else:
            proposal_id = args["proposalId"]
        old = await self._proposal_at(proposal_id, receipt)
        latest = await self._proposal_at(proposal_id, current)
        require(old is not None and latest is not None, "proposal absent after successful mutation")
        require(
            old["proposal"] == latest["proposal"]
            and latest["approvals"][: len(old["approvals"])] == old["approvals"]
            and (not old["executed"] or latest["executed"]),
            "proposal history regressed",
        )
        if evidence["function"] == "propose":
            require(old["proposal"] == args["proposal"], "created proposal tuple mismatch")
        else:
            require(evidence["sender"] in old["approvals"], "approval sender absent")
            count = old["approvals"].index(evidence["sender"]) + 1
            events = [
                {
                    "name": "ProposalApproved",
                    "arguments": {
                        "proposalId": proposal_id,
                        "approver": evidence["sender"],
                        "count": count,
                    },
                }
            ]
            if count == 2:
                events.append(
                    {
                        "name": "ProposalExecuted",
                        "arguments": {
                            "proposalId": proposal_id,
                            "issuerId": old["proposal"]["issuerId"],
                            "action": old["proposal"]["action"],
                        },
                    }
                )
            self._events(evidence, events)
        return old, latest

    async def _suspension(self, evidence, receipt, current):
        args = evidence["arguments"]
        require(
            args["reasonCode"]
            in {"0x" + keccak(text=x).hex() for x in ("KEY_COMPROMISE", "ABUSE_REPORT", "OTHER")},
            "unsupported suspension reason",
        )
        issuer_id = hex_bytes(args["issuerId"], 32)
        old = await self.rpc.call("getIssuer", [issuer_id], receipt)
        latest = await self.rpc.call("getIssuer", [issuer_id], current)
        require(
            old is not None and latest is not None and old[0] == 2,
            "suspension receipt-block state absent/ambiguous",
        )
        require(latest[0] in (1, 2), "invalid current issuer state")
        if evidence["events"]:
            self._events(
                evidence,
                [
                    {
                        "name": "IssuerSuspended",
                        "arguments": {
                            **args,
                            "actor": evidence["sender"],
                        },
                    }
                ],
            )
        if args["reasonCode"] == "0x" + keccak(text="KEY_COMPROMISE").hex():
            key = await self.rpc.call("getKey", [old[1]], receipt)
            require(
                key is not None
                and key[0][0] == issuer_id
                and 0 < key[0][4] <= quantity(receipt["number"]),
                "compromised key history missing/ambiguous",
            )
        return old, latest
