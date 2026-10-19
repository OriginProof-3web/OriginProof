"""B reconciliation against synthetic RPC; these are not live contract/API tests."""

import copy
import json

import httpx
import pytest
from eth_abi import decode, encode
from eth_utils import keccak
from infrastructure.blockchain.errors import (
    BlockchainConfigurationError,
    BlockchainDependencyError,
)
from infrastructure.blockchain.wallet_reconciliation import WalletReconciler
from infrastructure.blockchain.wallet_rpc import WalletRpc, abi_type, named, signature
from test_wallet_chain import ABI, ADDRESS, CODE, H1, H2, H3, SENDER, TX, Chain, block

ISSUER, KEY, DOC_KEY = b"i" * 32, b"k" * 32, b"d" * 32
DOC_ID = keccak(encode(["bytes32", "bytes32"], [ISSUER, DOC_KEY]))
OTHER = "0x" + "56" * 20
PROPOSAL = (1, ISSUER, KEY, SENDER, b"m" * 32, 0, 1000)
PROPOSAL_TYPE = next(x for x in ABI if x.get("name") == "getProposal")["outputs"][0]
PID = (
    "0x"
    + keccak(
        encode(["uint256", "address", abi_type(PROPOSAL_TYPE)], [31337, ADDRESS, PROPOSAL])
    ).hex()
)
PUBLISH = (
    1,
    ISSUER,
    DOC_KEY,
    DOC_ID,
    1,
    KEY,
    b"o" * 32,
    b"p" * 32,
    b"c" * 32,
    b"s" * 32,
    1,
    1,
    90,
    1000,
    0,
    200,
)
REVOKE = (2, ISSUER, DOC_KEY, DOC_ID, 1, KEY, 1, 200)
DOC = (ISSUER, DOC_KEY, 1, KEY, b"o" * 32, b"p" * 32, b"c" * 32, 90, 1000, 100, 2, 1)


def event(name, args, *, number=2, index=0, tx=TX):
    entry = next(x for x in ABI if x.get("name") == name and x["type"] == "event")
    topics, fields, values = ["0x" + keccak(text=signature(entry)).hex()], [], []
    for field in entry["inputs"]:
        value = args[field["name"]]
        if field["type"] == "bytes32" and isinstance(value, str):
            value = bytes.fromhex(value[2:])
        if field["indexed"]:
            topics.append("0x" + encode([field["type"]], [value]).hex())
        else:
            fields.append(field["type"])
            values.append(value)
    return {
        "address": ADDRESS,
        "topics": topics,
        "data": "0x" + encode(fields, values).hex(),
        "blockNumber": hex(number),
        "blockHash": H1 if number == 1 else H2,
        "transactionHash": tx,
        "logIndex": hex(index),
        "removed": False,
    }


class Oracle(Chain):
    def __init__(self):
        super().__init__()
        self.views = {
            "getDocument": (DOC,),
            "latestVersion": (1,),
            "nextNonce": (2,),
            "getIssuer": (1, KEY, SENDER, b"m" * 32),
            "getKey": ((ISSUER, SENDER, 1, 0, 0),),
            "getProposal": (PROPOSAL, 0, False),
        }
        self.reverts = {}
        self.selectors = {
            "0x" + keccak(text=signature(x))[:4].hex(): x for x in ABI if x["type"] == "function"
        }
        self.install(
            "publish",
            [PUBLISH, b"z" * 65],
            [
                event(
                    "DocumentPublished",
                    {
                        "documentId": DOC_ID,
                        "version": 1,
                        "issuerId": ISSUER,
                    },
                )
            ],
        )

    def install(self, function, values, logs):
        entry = next(x for x in ABI if x.get("name") == function and x["type"] == "function")
        self.tx["input"] = (
            "0x"
            + (
                keccak(text=signature(entry))[:4]
                + encode(
                    [abi_type(x) for x in entry["inputs"]],
                    values,
                )
            ).hex()
        )
        self.logs, self.receipt["logs"] = logs, logs
        self.intent = named(
            entry["inputs"],
            decode(
                [abi_type(x) for x in entry["inputs"]],
                bytes.fromhex(self.tx["input"][10:]),
            ),
        )
        return self.intent

    def handle(self, request):
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        if method in {"eth_call", "eth_getLogs"}:
            self.calls.append((method, params))
            result = {"jsonrpc": "2.0", "id": body["id"]}
            if method == "eth_call":
                entry = self.selectors[params[0]["data"][:10]]
                name = entry["name"]
                if name in self.reverts:
                    result["error"] = {"code": 3, "data": self.reverts[name]}
                else:
                    values = self.views.get((params[1]["blockHash"], name), self.views[name])
                    result["result"] = (
                        "0x"
                        + encode(
                            [abi_type(x) for x in entry["outputs"]],
                            values,
                        ).hex()
                    )
            else:
                result["result"] = [
                    x
                    for x in self.logs
                    if int(params[0]["fromBlock"], 16)
                    <= int(x["blockNumber"], 16)
                    <= int(params[0]["toBlock"], 16)
                ]
            return httpx.Response(200, json=result)
        return super().handle(request)


@pytest.fixture
async def env():
    oracle = Oracle()
    async with httpx.AsyncClient(transport=httpx.MockTransport(oracle.handle)) as client:
        rpc = WalletRpc(
            client,
            "http://chain.test",
            chain_id=31337,
            address=ADDRESS,
            deployment_block=1,
            deployment_hash=H1,
            runtime_code_hash="0x" + keccak(CODE).hex(),
            abi=ABI,
        )
        yield oracle, rpc, WalletReconciler(rpc)


@pytest.mark.parametrize(
    "name,error,args",
    [
        ("getIssuer", "UnknownIssuer", [ISSUER]),
        ("getKey", "UnknownKey", [KEY]),
        ("getDocument", "UnknownDocument", [DOC_ID, 1]),
        ("getProposal", "UnknownProposal", [bytes.fromhex(PID[2:])]),
    ],
)
async def test_only_matching_missing_error_is_absent(env, name, error, args):
    oracle, rpc, _ = env
    oracle.reverts[name] = "0x" + keccak(text=error + "()")[:4].hex()
    assert (await rpc.read(name, args))["values"] is None
    oracle.reverts[name] = "0x" + keccak(text="Unauthorized()")[:4].hex()
    with pytest.raises(BlockchainDependencyError):
        await rpc.read(name, args)


@pytest.mark.parametrize(
    "data",
    [
        None,
        "0x",
        "0xdeadbeef",
        "bad",
        {"data": "0x"},
        "0x" + (keccak(text="UnknownIssuer()")[:4] + b"junk").hex(),
    ],
)
async def test_bad_or_unrelated_revert_never_means_absent(env, data):
    oracle, rpc, _ = env
    oracle.reverts["getIssuer"] = data
    with pytest.raises(BlockchainDependencyError):
        await rpc.read("getIssuer", [ISSUER])


async def test_absent_rechecks_canonical_hash(env):
    oracle, rpc, _ = env
    head = await rpc.snapshot()
    oracle.blocks["0x2"] = block(2, H3)
    oracle.reverts["getIssuer"] = "0x" + keccak(text="UnknownIssuer()")[:4].hex()
    with pytest.raises(BlockchainDependencyError):
        await rpc.call("getIssuer", [ISSUER], head)


def proposal_logs(approvals=2):
    logs = [
        event(
            "ProposalCreated", {"proposalId": PID, "issuerId": ISSUER, "action": 1}, number=1, tx=H1
        )
    ]
    for index, actor in enumerate((OTHER, SENDER)[:approvals]):
        logs.append(
            event(
                "ProposalApproved",
                {"proposalId": PID, "approver": actor, "count": index + 1},
                index=index,
                tx=TX if index == approvals - 1 else H3,
            )
        )
    if approvals == 2:
        logs.append(
            event("ProposalExecuted", {"proposalId": PID, "issuerId": ISSUER, "action": 1}, index=2)
        )
    return logs


@pytest.mark.parametrize("count", [0, 1, 2])
async def test_proposal_list_count_and_execution_same_snapshot(env, count):
    oracle, _, reconciler = env
    oracle.logs = proposal_logs(count)
    oracle.views["getProposal"] = (PROPOSAL, count, count == 2)
    result = await reconciler.proposal(PID)
    assert result["approvals"] == [OTHER, SENDER][:count]
    assert result["executed"] == (count == 2)


@pytest.mark.parametrize(
    "kind",
    [
        "missing_creation",
        "missing_approval",
        "missing_execution",
        "count",
        "duplicate",
        "wrong_issuer",
        "wrong_tx",
        "tuple",
    ],
)
async def test_inconsistent_approval_history_is_dependency_failure(env, kind):
    oracle, _, reconciler = env
    oracle.logs = proposal_logs()
    oracle.views["getProposal"] = (PROPOSAL, 2, True)
    if kind == "missing_creation":
        oracle.logs.pop(0)
    elif kind == "missing_approval":
        oracle.logs.pop(1)
    elif kind == "missing_execution":
        oracle.logs.pop()
    elif kind == "count":
        oracle.views["getProposal"] = (PROPOSAL, 1, True)
    elif kind == "duplicate":
        oracle.logs[2] = event(
            "ProposalApproved", {"proposalId": PID, "approver": OTHER, "count": 2}, index=1
        )
    elif kind == "wrong_issuer":
        oracle.logs[0] = event(
            "ProposalCreated", {"proposalId": PID, "issuerId": KEY, "action": 1}, number=1
        )
    elif kind == "wrong_tx":
        oracle.logs[-1]["transactionHash"] = H3
    else:
        oracle.views["getProposal"] = ((2, *PROPOSAL[1:]), 2, True)
    with pytest.raises(BlockchainDependencyError):
        await reconciler.proposal(PID)


async def test_publish_reconciles_actual_intent_event_state_and_current_history(env):
    oracle, _, reconciler = env
    result = await reconciler.transaction(TX, function="publish", arguments=oracle.intent)
    assert result["receipt_state"]["document"]["originalHash"] == "0x" + "6f" * 32
    assert result["current_state"]["document"]["state"] == 1
    assert not any(x[0].startswith("eth_send") for x in oracle.calls)


@pytest.mark.parametrize(
    "kind",
    ["intent", "sender", "event", "hash", "nonce", "position", "ownership", "key", "inclusion"],
)
async def test_publish_rejects_partial_or_forged_evidence(env, kind):
    oracle, _, reconciler = env
    intent, sender = copy.deepcopy(oracle.intent), None
    if kind == "intent":
        intent["message"]["originalHash"] = "0x" + "ff" * 32
    elif kind == "sender":
        sender = OTHER
    elif kind == "event":
        oracle.receipt["logs"] = []
    elif kind == "hash":
        oracle.views["getDocument"] = ((*DOC[:4], b"f" * 32, *DOC[5:]),)
    elif kind == "nonce":
        oracle.views["nextNonce"] = (0,)
    elif kind == "position":
        oracle.views["getDocument"] = ((*DOC[:10], 1, 1),)
    elif kind == "ownership":
        oracle.views["getDocument"] = ((KEY, *DOC[1:]),)
    elif kind == "key":
        oracle.views["getKey"] = ((KEY, SENDER, 1, 0, 0),)
    else:
        oracle.blocks["0x2"]["transactions"] = [H3]
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(TX, function="publish", arguments=intent, sender=sender)


async def test_later_revocation_and_suspension_remain_visible(env):
    oracle, _, reconciler = env
    oracle.head, oracle.blocks["0x3"] = "0x3", block(3, H3)
    oracle.views[(H3, "getDocument")] = ((*DOC[:-1], 2),)
    oracle.views[(H3, "getIssuer")] = (2, KEY, SENDER, b"m" * 32)
    oracle.views[(H3, "getKey")] = ((ISSUER, SENDER, 1, 0, 3),)
    result = await reconciler.transaction(TX, function="publish", arguments=oracle.intent)
    assert result["receipt_state"]["document"]["state"] == 1
    assert result["current_state"]["document"]["state"] == 2
    assert result["current_state"]["issuer"][0] == 2
    assert result["current_state"]["publication_key"][4] == 3


async def test_revoke_superseded_history_and_pending_failed(env):
    oracle, _, reconciler = env
    intent = oracle.install(
        "revoke",
        [REVOKE, b"z" * 65],
        [
            event(
                "DocumentRevoked",
                {
                    "documentId": DOC_ID,
                    "version": 1,
                    "issuerId": ISSUER,
                },
            )
        ],
    )
    oracle.views["getDocument"] = ((*DOC[:-1], 2),)
    oracle.views["latestVersion"] = (2,)
    assert (await reconciler.transaction(TX, function="revoke", arguments=intent))["current_state"][
        "document"
    ]["state"] == 2
    oracle.receipt["status"], oracle.receipt["logs"] = "0x0", []
    result = await reconciler.transaction(TX, function="revoke", arguments=intent)
    assert result["receipt_status"] == 0 and "current_state" not in result
    oracle.receipt = None
    assert await reconciler.transaction(TX, function="revoke", arguments=intent) is None


async def test_approve_second_and_propose_reconcile(env):
    oracle, _, reconciler = env
    logs = proposal_logs()
    oracle.install("approve", [bytes.fromhex(PID[2:])], logs[2:])
    oracle.logs = logs
    oracle.views["getProposal"] = (PROPOSAL, 2, True)
    result = await reconciler.transaction(
        TX, function="approve", arguments=oracle.intent, sender=oracle.tx["from"]
    )
    assert result["receipt_state"]["executed"]
    # Creation is matched against the exact immutable proposal tuple.
    created = event("ProposalCreated", {"proposalId": PID, "issuerId": ISSUER, "action": 1})
    proof = (3, b"a" * 32, ISSUER, SENDER, b"h" * 32, 1000)
    oracle.install("propose", [PROPOSAL, proof, b"z" * 65], [created])
    oracle.views["getProposal"] = (PROPOSAL, 0, False)
    assert (
        await reconciler.transaction(
            TX, function="propose", arguments=oracle.intent, sender=oracle.tx["from"]
        )
    )["receipt_state"]["proposal"]["issuerId"] == "0x" + ISSUER.hex()


@pytest.mark.parametrize("noop", [False, True])
async def test_suspension_changed_or_already_suspended(env, noop):
    oracle, _, reconciler = env
    reason = keccak(text="OTHER")
    logs = (
        []
        if noop
        else [event("IssuerSuspended", {"issuerId": ISSUER, "actor": SENDER, "reasonCode": reason})]
    )
    oracle.install("suspendIssuer", [ISSUER, reason], logs)
    oracle.views["getIssuer"] = (2, KEY, SENDER, b"m" * 32)
    result = await reconciler.transaction(
        TX, function="suspendIssuer", arguments=oracle.intent, sender=oracle.tx["from"]
    )
    assert result["receipt_state"][0] == 2
    oracle.views["getIssuer"] = (1, KEY, SENDER, b"m" * 32)
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(
            TX, function="suspendIssuer", arguments=oracle.intent, sender=oracle.tx["from"]
        )


async def test_full_intent_rejects_numeric_type_alias_and_missing_signature(env):
    oracle, _, reconciler = env
    intent = copy.deepcopy(oracle.intent)
    intent["message"]["nonce"] = False
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(TX, function="publish", arguments=intent)
    intent = {"message": oracle.intent["message"]}
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(TX, function="publish", arguments=intent)


async def test_unknown_selector_from_wrong_getter_is_not_absent(env):
    oracle, rpc, _ = env
    oracle.reverts["getKey"] = "0x" + keccak(text="UnknownIssuer()")[:4].hex()
    with pytest.raises(BlockchainDependencyError):
        await rpc.read("getKey", [KEY])


async def test_next_version_requires_atomic_superseded_event(env):
    oracle, _, reconciler = env
    publication = (*PUBLISH[:4], 2, *PUBLISH[5:])
    logs = [
        event("DocumentSuperseded", {"documentId": DOC_ID, "version": 1, "replacement": 2}),
        event(
            "DocumentPublished", {"documentId": DOC_ID, "version": 2, "issuerId": ISSUER}, index=1
        ),
    ]
    oracle.install("publish", [publication, b"z" * 65], logs)
    oracle.views["getDocument"] = ((*DOC[:2], 2, *DOC[3:]),)
    oracle.views["latestVersion"] = (2,)
    result = await reconciler.transaction(TX, function="publish", arguments=oracle.intent)
    assert result["receipt_state"]["latest_version"] == 2
    oracle.receipt["logs"] = logs[1:]
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(TX, function="publish", arguments=oracle.intent)


async def test_publish_then_superseded_keeps_current_state_separate(env):
    oracle, _, reconciler = env
    oracle.head, oracle.blocks["0x3"] = "0x3", block(3, H3)
    oracle.views[(H3, "getDocument")] = ((*DOC[:-1], 3),)
    oracle.views[(H3, "latestVersion")] = (2,)
    result = await reconciler.transaction(TX, function="publish", arguments=oracle.intent)
    assert result["current_state"]["document"]["state"] == 3
    assert result["current_state"]["latest_version"] == 2


async def test_revoke_stays_revoked_after_later_publish(env):
    oracle, _, reconciler = env
    oracle.install(
        "revoke",
        [REVOKE, b"z" * 65],
        [
            event(
                "DocumentRevoked",
                {
                    "documentId": DOC_ID,
                    "version": 1,
                    "issuerId": ISSUER,
                },
            )
        ],
    )
    oracle.views["getDocument"] = ((*DOC[:-1], 2),)
    oracle.head, oracle.blocks["0x3"] = "0x3", block(3, H3)
    oracle.views[(H3, "getDocument")] = ((*DOC[:-1], 3),)
    oracle.views[(H3, "latestVersion")] = (2,)
    with pytest.raises(BlockchainDependencyError, match="resurrected"):
        await reconciler.transaction(TX, function="revoke", arguments=oracle.intent)
    oracle.views[(H3, "getDocument")] = ((*DOC[:-1], 2),)
    result = await reconciler.transaction(TX, function="revoke", arguments=oracle.intent)
    assert result["current_state"]["document"]["state"] == 2
    oracle.views[(H3, "getDocument")] = (DOC,)
    oracle.views[(H3, "latestVersion")] = (1,)
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(TX, function="revoke", arguments=oracle.intent)


async def test_historical_publish_block_end_revoked_is_not_current_active(env):
    oracle, _, reconciler = env
    oracle.views["getDocument"] = ((*DOC[:-1], 2),)
    result = await reconciler.transaction(TX, function="publish", arguments=oracle.intent)
    assert result["receipt_state"]["document"]["state"] == 2
    assert result["current_state"]["document"]["state"] == 2


async def test_current_nonce_or_immutable_regression_fails(env):
    oracle, _, reconciler = env
    oracle.head, oracle.blocks["0x3"] = "0x3", block(3, H3)
    oracle.views[(H3, "nextNonce")] = (1,)
    with pytest.raises(BlockchainDependencyError, match="history regressed"):
        await reconciler.transaction(TX, function="publish", arguments=oracle.intent)
    oracle.views[(H3, "nextNonce")] = (2,)
    oracle.views[(H3, "getDocument")] = ((*DOC[:4], b"f" * 32, *DOC[5:]),)
    with pytest.raises(BlockchainDependencyError, match="history regressed"):
        await reconciler.transaction(TX, function="publish", arguments=oracle.intent)


async def test_first_approval_can_observe_execution_later_in_same_block(env):
    oracle, _, reconciler = env
    logs = proposal_logs()
    oracle.install("approve", [bytes.fromhex(PID[2:])], [logs[1]])
    oracle.tx["from"], oracle.receipt["from"] = OTHER, OTHER
    logs[1]["transactionHash"] = TX
    logs[2]["transactionHash"] = logs[3]["transactionHash"] = H3
    oracle.logs = logs
    oracle.views["getProposal"] = (PROPOSAL, 2, True)
    result = await reconciler.transaction(
        TX, function="approve", arguments=oracle.intent, sender=oracle.tx["from"]
    )
    assert result["receipt_state"]["approvals"] == [OTHER, SENDER]
    assert result["receipt_state"]["executed"]


async def test_second_approval_missing_execution_receipt_fails(env):
    oracle, _, reconciler = env
    logs = proposal_logs()
    oracle.install("approve", [bytes.fromhex(PID[2:])], [logs[2]])
    oracle.logs = logs
    oracle.views["getProposal"] = (PROPOSAL, 2, True)
    with pytest.raises(BlockchainDependencyError, match="event sequence"):
        await reconciler.transaction(
            TX, function="approve", arguments=oracle.intent, sender=oracle.tx["from"]
        )


async def test_key_compromise_requires_history_and_noop_preserves_it(env):
    oracle, _, reconciler = env
    reason = keccak(text="KEY_COMPROMISE")
    oracle.install("suspendIssuer", [ISSUER, reason], [])
    oracle.views["getIssuer"] = (2, KEY, SENDER, b"m" * 32)
    with pytest.raises(BlockchainDependencyError, match="compromised key history"):
        await reconciler.transaction(
            TX, function="suspendIssuer", arguments=oracle.intent, sender=oracle.tx["from"]
        )
    oracle.views["getKey"] = ((ISSUER, SENDER, 1, 0, 2),)
    result = await reconciler.transaction(
        TX, function="suspendIssuer", arguments=oracle.intent, sender=oracle.tx["from"]
    )
    assert result["receipt_state"][0] == 2


async def test_later_reactivation_does_not_erase_historical_suspension(env):
    oracle, _, reconciler = env
    oracle.install("suspendIssuer", [ISSUER, keccak(text="OTHER")], [])
    oracle.views["getIssuer"] = (2, KEY, SENDER, b"m" * 32)
    oracle.head, oracle.blocks["0x3"] = "0x3", block(3, H3)
    oracle.views[(H3, "getIssuer")] = (1, KEY, SENDER, b"m" * 32)
    result = await reconciler.transaction(
        TX, function="suspendIssuer", arguments=oracle.intent, sender=oracle.tx["from"]
    )
    assert result["receipt_state"][0] == 2 and result["current_state"][0] == 1


async def test_rpc_outage_in_reconciliation_cannot_use_cached_journal(env):
    oracle, _, reconciler = env
    oracle.reverts["getDocument"] = "0xdeadbeef"
    with pytest.raises(BlockchainDependencyError):
        await reconciler.transaction(TX, function="publish", arguments=oracle.intent)


@pytest.mark.parametrize("function", ["approve", "propose", "suspendIssuer"])
async def test_governance_requires_stored_expected_sender(env, function):
    _, _, reconciler = env
    with pytest.raises(BlockchainConfigurationError, match="sender is required"):
        await reconciler.transaction(TX, function=function, arguments={})
