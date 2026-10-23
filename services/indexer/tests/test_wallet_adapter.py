"""Real B RPC decoding + C DTO/factory, synthetic transport; no live API/DB claim."""

import httpx
import pytest
from eth_utils import keccak
from fastapi import HTTPException
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_rpc import WalletRpc
from originproof_api.database import Database
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_core import DependencyUnavailableError
from originproof_core.wallet_contract import PublishMessage
from originproof_core.wallet_ports import WalletDocument, WalletIssuer, WalletKey, WalletProposal
from test_wallet_chain import ABI, ADDRESS, CODE, H1, H2, H3, TX, block
from test_wallet_reconciliation import (
    DOC,
    DOC_ID,
    ISSUER,
    KEY,
    OTHER,
    PID,
    PROPOSAL,
    SENDER,
    Oracle,
    proposal_logs,
)

IID, KID, DID = ["0x" + x.hex() for x in (ISSUER, KEY, DOC_ID)]


@pytest.fixture
async def adapter_env():
    oracle = Oracle()
    oracle.views["governanceNonce"] = (0,)
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
        yield oracle, rpc, WalletRegistryReadAdapter(rpc)


async def test_original_models_and_same_block_position(adapter_env):
    oracle, _, adapter = adapter_env
    issuer = await adapter.issuer(IID)
    key = await adapter.key(KID)
    doc = await adapter.document(DID, None)
    assert isinstance(issuer, WalletIssuer) and isinstance(key, WalletKey)
    assert isinstance(doc, WalletDocument)
    for value in (issuer, key, doc):
        assert value.chain_id == "31337" and value.verifying_contract == ADDRESS
        assert value.block_number == "2" and value.block_hash == H2
    assert issuer.next_nonce == "2" and issuer.governance_nonce == "0"
    assert issuer.key_id == key.key_id == doc.document.key_id == KID
    assert doc.document.state == "ACTIVE" and doc.document.warnings == []
    assert doc.document.original_available is False
    assert key.retired_block is key.compromise_block is None
    assert all(
        params[1] == {"blockHash": H2, "requireCanonical": True}
        for method, params in oracle.calls
        if method == "eth_call"
    )


@pytest.mark.parametrize(
    "method,getter,error,identifier",
    [
        ("issuer", "getIssuer", "UnknownIssuer", IID),
        ("key", "getKey", "UnknownKey", KID),
        ("proposal", "getProposal", "UnknownProposal", PID),
    ],
)
async def test_only_matching_custom_error_is_absent(adapter_env, method, getter, error, identifier):
    oracle, _, adapter = adapter_env
    oracle.reverts[getter] = "0x" + keccak(text=error + "()")[:4].hex()
    assert await getattr(adapter, method)(identifier) is None
    oracle.reverts[getter] = "0x" + keccak(text="UnknownDocument()")[:4].hex()
    with pytest.raises(DependencyUnavailableError):
        await getattr(adapter, method)(identifier)


async def test_unknown_latest_and_future_version_are_absent(adapter_env):
    oracle, _, adapter = adapter_env
    oracle.views["latestVersion"] = (0,)
    assert await adapter.document(DID, None) is None
    oracle.reverts["getDocument"] = "0x" + keccak(text="UnknownDocument()")[:4].hex()
    assert await adapter.document(DID, 1) is None
    oracle.views["latestVersion"] = (1,)
    assert await adapter.document(DID, 2) is None
    with pytest.raises(DependencyUnavailableError):
        await adapter.document(DID, 1)


@pytest.mark.parametrize(
    "state,latest,expires,expected",
    [
        (1, 1, 1000, "ACTIVE"),
        (1, 1, 100, "EXPIRED"),
        (2, 1, 100, "REVOKED"),
        (3, 2, 100, "SUPERSEDED"),
    ],
)
async def test_state_expiry_and_warnings_are_independent(
    adapter_env, state, latest, expires, expected
):
    oracle, _, adapter = adapter_env
    doc = list(DOC)
    doc[8] = expires
    doc[-1] = state
    oracle.views["getDocument"] = (tuple(doc),)
    oracle.views["latestVersion"] = (latest,)
    oracle.views["getIssuer"] = (2, KEY, SENDER, b"m" * 32)
    oracle.views["getKey"] = ((ISSUER, SENDER, 1, 0, 2),)
    result = await adapter.document(DID, 1)
    assert result.document.state == expected
    assert result.document.warnings == ["ISSUER_SUSPENDED", "KEY_COMPROMISED"]
    assert result.document.original_available is False


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_owner",
        "wrong_version",
        "active_old",
        "superseded_latest",
        "future_publication",
        "future_time",
        "key_owner",
        "key_registered_late",
        "key_history_future",
        "bad_enum",
    ],
)
async def test_inconsistent_document_never_becomes_success(adapter_env, fault):
    oracle, _, adapter = adapter_env
    doc = list(DOC)
    if fault == "wrong_owner":
        doc[0] = b"x" * 32
    elif fault == "wrong_version":
        doc[2] = 2
    elif fault == "active_old":
        oracle.views["latestVersion"] = (2,)
    elif fault == "superseded_latest":
        doc[-1] = 3
    elif fault == "future_publication":
        doc[-2] = 3
    elif fault == "future_time":
        doc[-3] = 101
    elif fault == "key_owner":
        oracle.views["getKey"] = ((b"x" * 32, SENDER, 1, 0, 0),)
    elif fault == "key_registered_late":
        oracle.views["getKey"] = ((ISSUER, SENDER, 3, 0, 0),)
    elif fault == "key_history_future":
        oracle.views["getKey"] = ((ISSUER, SENDER, 1, 0, 3),)
    elif fault == "bad_enum":
        doc[-1] = 0
    oracle.views["getDocument"] = (tuple(doc),)
    with pytest.raises(DependencyUnavailableError):
        await adapter.document(DID, 1)


@pytest.mark.parametrize("fault", ["state", "signer", "key_owner", "retired", "missing_key"])
async def test_current_issuer_requires_matching_current_key(adapter_env, fault):
    oracle, _, adapter = adapter_env
    if fault == "state":
        oracle.views["getIssuer"] = (0, KEY, SENDER, b"m" * 32)
    elif fault == "signer":
        oracle.views["getKey"] = ((ISSUER, OTHER, 1, 0, 0),)
    elif fault == "key_owner":
        oracle.views["getKey"] = ((b"x" * 32, SENDER, 1, 0, 0),)
    elif fault == "retired":
        oracle.views["getKey"] = ((ISSUER, SENDER, 1, 2, 0),)
    else:
        oracle.reverts["getKey"] = "0x" + keccak(text="UnknownKey()")[:4].hex()
    with pytest.raises(DependencyUnavailableError):
        await adapter.issuer(IID)


@pytest.mark.parametrize(
    "count,nonce,timestamp,expected",
    [
        (0, 0, 100, "PENDING"),
        (1, 0, 100, "PENDING"),
        (2, 1, 100, "EXECUTED"),
        (0, 0, 1000, "EXPIRED"),
        (1, 1, 100, "STALE"),
        (2, 1, 1000, "EXECUTED"),
    ],
)
async def test_proposal_status_uses_original_model_and_canonical_approvals(
    adapter_env,
    count,
    nonce,
    timestamp,
    expected,
):
    oracle, _, adapter = adapter_env
    oracle.blocks["0x2"]["timestamp"] = hex(timestamp)
    oracle.logs = proposal_logs(count)
    oracle.views["getProposal"] = (PROPOSAL, count, count == 2)
    oracle.views["governanceNonce"] = (nonce,)
    result = await adapter.proposal(PID)
    assert isinstance(result, WalletProposal)
    assert result.proposal.status == expected
    assert result.proposal.proposal.nonce == "0"
    assert result.proposal.approvals == [OTHER, SENDER][:count]


async def test_transaction_returns_actual_arguments_in_C_format(adapter_env):
    oracle, _, adapter = adapter_env
    actual = await adapter.transaction(TX)
    message = PublishMessage.model_validate(actual.arguments["message"])
    assert actual.action == "Publish" and actual.status == "CONFIRMED"
    assert message.nonce == "0" and actual.sender == SENDER
    assert actual.arguments["signature"] == oracle.intent["signature"]
    assert actual.arguments["message"]["version"] == 1
    oracle.receipt["status"] = "0x0"
    oracle.receipt["logs"] = []
    assert (await adapter.transaction(TX)).status == "FAILED"
    oracle.tx = None
    assert await adapter.transaction(TX) is None


async def test_reorg_is_dependency_not_absent(adapter_env, monkeypatch):
    oracle, rpc, adapter = adapter_env
    original = rpc.check
    calls = 0

    async def reorg_at_end(head):
        nonlocal calls
        calls += 1
        if calls > 1:
            oracle.blocks["0x2"] = block(2, H3)
        await original(head)

    monkeypatch.setattr(rpc, "check", reorg_at_end)
    with pytest.raises(DependencyUnavailableError):
        await adapter.key(KID)


@pytest.mark.parametrize(
    "method,args", [("is_approver", [SENDER]), ("submit", [None, "0x"]), ("find_transaction", [{}])]
)
async def test_unconfigured_paths_fail_closed(adapter_env, method, args):
    oracle, _, adapter = adapter_env
    with pytest.raises(DependencyUnavailableError):
        await getattr(adapter, method)(*args)
    assert not any(name.startswith("eth_send") for name, _ in oracle.calls)


async def test_C_factory_injection_and_503_translation(adapter_env):
    oracle, _, adapter = adapter_env
    database = Database("postgresql+asyncpg://localhost/originproof_adapter_unit")
    try:
        app = create_app(
            database=database,
            settings=Settings(wallet_registry_address=ADDRESS),
            wallet_chain=adapter,
        )
        runtime = app.state.wallet_runtime
        assert runtime.chain is adapter
        assert isinstance(await runtime.rpc("issuer", IID), WalletIssuer)
        oracle.override = (
            lambda name, body: {**body, "result": "0x1"} if name == "eth_chainId" else body
        )
        with pytest.raises(HTTPException) as exc:
            await runtime.rpc("issuer", IID)
        assert exc.value.status_code == 503
        assert exc.value.detail == "WALLET_REGISTRY_UNAVAILABLE"
        with pytest.raises(HTTPException) as exc:
            await runtime.rpc("submit", None, "0x")
        assert exc.value.status_code == 503
    finally:
        await database.dispose()


@pytest.mark.parametrize(
    "method,args",
    [
        ("key", ["bad"]),
        ("issuer", [IID.upper()]),
        ("document", [DID, True]),
        ("document", [DID, 0]),
        ("transaction", ["0x1"]),
    ],
)
async def test_invalid_inputs_do_not_escape_C_error_boundary(adapter_env, method, args):
    _, _, adapter = adapter_env
    with pytest.raises(DependencyUnavailableError):
        await getattr(adapter, method)(*args)


async def test_large_nonce_and_normal_key_rotation_preserve_history(adapter_env):
    oracle, _, adapter = adapter_env
    oracle.views["nextNonce"] = (2**200,)
    oracle.views["governanceNonce"] = (2**180,)
    current = await adapter.issuer(IID)
    assert current.next_nonce == str(2**200) and current.governance_nonce == str(2**180)
    oracle.views["getKey"] = ((ISSUER, SENDER, 1, 2, 0),)
    history = await adapter.document(DID, 1)
    assert history.document.state == "ACTIVE" and history.document.warnings == []
    assert (await adapter.key(KID)).retired_block == "2"
