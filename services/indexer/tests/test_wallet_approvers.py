"""Synthetic CREATE proof binding and C error translation; no production chain claim."""

import copy

import httpx
import pytest
from eth_abi import encode
from eth_utils import keccak
from fastapi import HTTPException
from infrastructure.blockchain.errors import BlockchainConfigurationError
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_creation import WalletCreationProof
from infrastructure.blockchain.wallet_rpc import WalletRpc
from originproof_api.database import Database
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_core import DependencyUnavailableError
from test_wallet_chain import ABI, ADDRESS, CODE, H1, H2, H3, SENDER, TX, Chain, block

SECOND, THIRD, OUTSIDER = ["0x" + x * 20 for x in ("56", "ab", "90")]
APPROVERS = (SENDER, SECOND, THIRD)
CREATION = b"trusted synthetic Registry initcode"


@pytest.fixture
async def creation_env():
    chain = Chain()
    chain.blocks["0x1"]["transactions"] = [TX]
    chain.blocks["0x2"]["transactions"] = []
    chain.tx = dict(
        hash=TX,
        to=None,
        chainId="0x7a69",
        value="0x0",
        blockHash=H1,
        blockNumber="0x1",
        transactionIndex="0x0",
        input="0x" + (CREATION + encode(["address[3]"], [APPROVERS])).hex(),
    )
    chain.tx["from"] = SENDER
    chain.receipt = dict(
        transactionHash=TX,
        to=None,
        contractAddress=ADDRESS,
        blockHash=H1,
        blockNumber="0x1",
        transactionIndex="0x0",
        status="0x1",
    )
    chain.receipt["from"] = SENDER
    async with httpx.AsyncClient(transport=httpx.MockTransport(chain.handle)) as client:
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
        proof = WalletCreationProof(TX, CREATION)
        yield chain, rpc, WalletRegistryReadAdapter(rpc, creation_proof=proof)


@pytest.mark.parametrize(
    "candidate,expected",
    [
        (SENDER, True),
        (SECOND, True),
        (THIRD, True),
        ("0x" + THIRD[2:].upper(), True),
        (OUTSIDER, False),
    ],
)
async def test_membership_comes_from_verified_actual_constructor(creation_env, candidate, expected):
    chain, _, adapter = creation_env
    assert await adapter.is_approver(candidate) is expected
    assert any(method == "eth_getTransactionReceipt" for method, _ in chain.calls)
    assert any(
        method == "eth_getCode" and params[1]["blockHash"] == H1 for method, params in chain.calls
    )
    assert not any(method.startswith("eth_send") for method, _ in chain.calls)


@pytest.mark.parametrize(
    "fault",
    [
        "missing_tx",
        "missing_receipt",
        "tx_hash",
        "receipt_hash",
        "tx_to",
        "receipt_to",
        "contract",
        "sender",
        "chain",
        "value",
        "tx_block_hash",
        "receipt_block_hash",
        "tx_height",
        "receipt_height",
        "index_mismatch",
        "missing_position",
        "wrong_position",
        "failed",
        "untrusted_initcode",
        "extra_bytes",
        "padding",
        "zero",
        "duplicate",
        "short_arguments",
        "missing_abi",
        "wrong_abi",
        "deployment_code",
        "current_code",
    ],
)
async def test_bad_provenance_never_authorizes_even_a_listed_wallet(creation_env, fault):
    chain, rpc, adapter = creation_env
    tx, receipt = chain.tx, chain.receipt
    if fault == "missing_tx":
        chain.tx = None
    elif fault == "missing_receipt":
        chain.receipt = None
    elif fault == "tx_hash":
        tx["hash"] = H3
    elif fault == "receipt_hash":
        receipt["transactionHash"] = H3
    elif fault == "tx_to":
        tx["to"] = ADDRESS
    elif fault == "receipt_to":
        receipt["to"] = ADDRESS
    elif fault == "contract":
        receipt["contractAddress"] = SECOND
    elif fault == "sender":
        receipt["from"] = SECOND
    elif fault == "chain":
        tx["chainId"] = "0x1"
    elif fault == "value":
        tx["value"] = "0x1"
    elif fault == "tx_block_hash":
        tx["blockHash"] = H3
    elif fault == "receipt_block_hash":
        receipt["blockHash"] = H3
    elif fault == "tx_height":
        tx["blockNumber"] = "0x2"
    elif fault == "receipt_height":
        receipt["blockNumber"] = "0x2"
    elif fault == "index_mismatch":
        receipt["transactionIndex"] = "0x1"
    elif fault == "missing_position":
        chain.blocks["0x1"]["transactions"] = []
    elif fault == "wrong_position":
        chain.blocks["0x1"]["transactions"] = [H3]
    elif fault == "failed":
        receipt["status"] = "0x0"
    elif fault == "untrusted_initcode":
        tx["input"] = "0x" + (b"x" + bytes.fromhex(tx["input"][4:])).hex()
    elif fault == "extra_bytes":
        tx["input"] += "00"
    elif fault == "padding":
        args = bytearray(encode(["address[3]"], [APPROVERS]))
        args[0] = 1
        tx["input"] = "0x" + (CREATION + args).hex()
    elif fault in ("zero", "duplicate"):
        roles = (SENDER, SECOND, "0x" + "00" * 20 if fault == "zero" else SECOND)
        tx["input"] = "0x" + (CREATION + encode(["address[3]"], [roles])).hex()
    elif fault == "short_arguments":
        tx["input"] = "0x" + CREATION.hex()
    elif fault == "missing_abi":
        rpc.constructor = None
    elif fault == "wrong_abi":
        rpc.constructor = copy.deepcopy(rpc.constructor)
        rpc.constructor["inputs"][0]["type"] = "address[2]"
    elif fault in ("deployment_code", "current_code"):
        target = H1 if fault == "deployment_code" else H2
        chain.override = (
            lambda method, body: {**body, "result": "0xdead"}
            if (method == "eth_getCode" and chain.calls[-1][1][1]["blockHash"] == target)
            else body
        )
    with pytest.raises(DependencyUnavailableError):
        await adapter.is_approver(SENDER)


async def test_verified_roles_are_not_cached_across_calls(creation_env):
    chain, _, adapter = creation_env
    assert await adapter.is_approver(SENDER)
    chain.receipt["status"] = "0x0"
    with pytest.raises(DependencyUnavailableError):
        await adapter.is_approver(SENDER)
    with pytest.raises(DependencyUnavailableError):
        await adapter.is_approver(OUTSIDER)


async def test_reorg_during_final_head_check_rejects_authorization(creation_env, monkeypatch):
    chain, rpc, adapter = creation_env
    check = rpc.check
    calls = 0

    async def changed_head_at_end(head):
        nonlocal calls
        calls += 1
        if calls == 3:
            chain.blocks["0x2"] = block(2, H3)
        await check(head)

    monkeypatch.setattr(rpc, "check", changed_head_at_end)
    with pytest.raises(DependencyUnavailableError):
        await adapter.is_approver(SENDER)


@pytest.mark.parametrize("candidate", ["0x" + "00" * 20, "not-an-address", None])
async def test_invalid_candidate_is_error_not_authorization(creation_env, candidate):
    _, _, adapter = creation_env
    with pytest.raises(DependencyUnavailableError):
        await adapter.is_approver(candidate)


@pytest.mark.parametrize("tx_hash,code", [("bad", CREATION), (TX, b""), (TX, "0x1234")])
def test_invalid_trust_configuration_is_rejected(tx_hash, code):
    with pytest.raises(BlockchainConfigurationError):
        WalletCreationProof(tx_hash, code)


async def test_C_factory_accepts_verified_boolean_and_maps_bad_proof_to_503(creation_env):
    chain, _, adapter = creation_env
    database = Database("postgresql+asyncpg://localhost/originproof_approver_unit")
    try:
        app = create_app(
            settings=Settings(wallet_registry_address=ADDRESS),
            database=database,
            wallet_chain=adapter,
        )
        assert await app.state.wallet_runtime.rpc("is_approver", SENDER) is True
        assert await app.state.wallet_runtime.rpc("is_approver", OUTSIDER) is False
        chain.receipt["contractAddress"] = SECOND
        with pytest.raises(HTTPException) as exc:
            await app.state.wallet_runtime.rpc("is_approver", SENDER)
        assert exc.value.status_code == 503
        assert exc.value.detail == "WALLET_REGISTRY_UNAVAILABLE"
    finally:
        await database.dispose()


async def test_creation_proof_cannot_be_a_plain_address_list(creation_env):
    _, rpc, _ = creation_env
    with pytest.raises(BlockchainConfigurationError):
        WalletRegistryReadAdapter(rpc, creation_proof=list(APPROVERS))


@pytest.mark.parametrize("fault", [None, "chain", "code", "creation", "missing_proof"])
async def test_adapter_initialization_verifies_deployment_before_injection(creation_env, fault):
    chain, rpc, original = creation_env
    deployment = dict(
        chain_id=rpc.chain_id,
        address=rpc.address,
        deployment_block=rpc.deployment_block,
        deployment_hash=rpc.deployment_hash,
        runtime_code_hash=rpc.runtime_code_hash,
        abi=ABI,
    )
    proof = original.creation_proof
    if fault == "chain":
        deployment["chain_id"] = 1
    elif fault == "code":
        deployment["runtime_code_hash"] = H3
    elif fault == "creation":
        proof = WalletCreationProof(TX, b"wrong trusted build")
    elif fault == "missing_proof":
        proof = None
    if fault is not None:
        with pytest.raises(DependencyUnavailableError):
            await WalletRegistryReadAdapter.from_deployment(
                rpc.client,
                rpc.url,
                creation_proof=proof,
                **deployment,
            )
    else:
        initialized = await WalletRegistryReadAdapter.from_deployment(
            rpc.client,
            rpc.url,
            creation_proof=proof,
            **deployment,
        )
        assert initialized.rpc.client is rpc.client
        assert not rpc.client.is_closed
        assert await initialized.is_approver(SENDER)
    assert not any(method.startswith("eth_send") for method, _ in chain.calls)
    if fault == "missing_proof":
        assert not chain.calls
