"""CHAIN_TARGET selection for projection/indexer and the wallet Registry deploy wrapper."""

import hashlib
import json
from types import SimpleNamespace

import deploy_wallet_registry as wrapper
import pytest
from infrastructure.blockchain.manifest import load_manifest
from infrastructure.blockchain.network import CHAIN_TARGETS, chain_target

APPROVERS = [
    "0x1111111111111111111111111111111111111111",
    "0x2222222222222222222222222222222222222222",
    "0x3333333333333333333333333333333333333333",
]
DEPLOYER = "0x4444444444444444444444444444444444444444"
REGISTRY = "0x5555555555555555555555555555555555555555"
TX = "0x" + "ab" * 32
BLOCK = "0x" + "cd" * 32
GENESIS = "0x" + "ef" * 32
SHA = "a" * 40
ABI = [
    {
        "type": "constructor",
        "inputs": [{"name": "approvers", "type": "address[3]", "internalType": "address[3]"}],
        "stateMutability": "nonpayable",
    },
    {"type": "function", "name": "approve", "inputs": [], "outputs": []},
]
# Fake forge artifact fixture: B's Registry is not on phase/W5, so no B file is copied here.
BYTECODE = "0x6080604052348015600e575f5ffd5b50" + "fe" * 16
OTHER_BYTECODE = "0x6080604052348015600e575f5ffd5b50" + "fd" * 16


def encode(addresses):
    return "".join(value[2:].lower().rjust(64, "0") for value in addresses)


def approver_env():
    return {f"WALLET_APPROVER_{i}_ADDRESS": value for i, value in enumerate(APPROVERS, 1)}


@pytest.mark.parametrize(
    ("name", "chain_id", "manifest"),
    [
        (None, 31337, "31337.wallet.local.json"),
        ("anvil", 31337, "31337.wallet.local.json"),
        ("sepolia", 11155111, "11155111.wallet.json"),
    ],
)
def test_chain_target_selects_chain_and_manifest(name, chain_id, manifest):
    target = chain_target(name)

    assert target.chain_id == chain_id
    assert target.wallet_manifest_path.name == manifest
    assert target.wallet_manifest_path.parent.name == "deployments"


@pytest.mark.parametrize("value", ["mainnet", "", "SEPOLIA", 1])
def test_unknown_chain_target_is_rejected(value):
    with pytest.raises(ValueError, match="CHAIN_TARGET must be one of: anvil, sepolia"):
        chain_target(value)


def test_projection_rejects_manifest_from_other_target(tmp_path):
    # The projection/indexer loads manifests with the chain ID derived from CHAIN_TARGET.
    path = tmp_path / "31337.local.json"
    path.write_text(json.dumps({"chain_id": 31337, "deployment_block": 1}))

    with pytest.raises(ValueError, match="wrong manifest chain"):
        load_manifest(path, CHAIN_TARGETS["sepolia"].chain_id)


@pytest.mark.parametrize(
    "env",
    [
        {},
        approver_env() | {"WALLET_APPROVER_3_ADDRESS": APPROVERS[0].upper().replace("0X", "0x")},
        approver_env() | {"WALLET_APPROVER_2_ADDRESS": "0x" + "0" * 40},
        approver_env() | {"WALLET_APPROVER_1_ADDRESS": "not-an-address"},
    ],
)
def test_approver_addresses_are_validated(env):
    with pytest.raises(ValueError):
        wrapper.approvers(env)


def signer(**values):
    defaults = dict(account=None, ledger=False, trezor=False, unlocked=False, sender=None)
    return SimpleNamespace(**(defaults | values))


@pytest.mark.parametrize(
    ("target", "args", "message"),
    [
        ("sepolia", signer(unlocked=True, sender=DEPLOYER), "only allowed for CHAIN_TARGET=anvil"),
        ("sepolia", signer(account="deployer", ledger=True), "choose one signer"),
        ("sepolia", signer(), "a signer is required"),
        ("anvil", signer(unlocked=True), "--unlocked requires --sender"),
    ],
)
def test_signer_choice_is_restricted(monkeypatch, target, args, message):
    monkeypatch.delenv("ETH_KEYSTORE_ACCOUNT", raising=False)

    with pytest.raises(ValueError, match=message):
        wrapper.signer_args(args, chain_target(target))


def test_signer_args_never_include_private_keys():
    sepolia = chain_target("sepolia")

    assert wrapper.signer_args(signer(account="deployer"), sepolia) == ["--account", "deployer"]
    assert wrapper.signer_args(signer(ledger=True, sender=DEPLOYER), sepolia) == [
        "--ledger",
        "--sender",
        DEPLOYER,
    ]
    assert wrapper.signer_args(signer(unlocked=True, sender=DEPLOYER), chain_target("anvil")) == [
        "--unlocked",
        "--sender",
        DEPLOYER,
    ]


def fake_rpc(chain_id=11155111, status="0x1", tx_input=None):
    answers = {
        "eth_chainId": hex(chain_id),
        "eth_getTransactionReceipt": {
            "status": status,
            "contractAddress": REGISTRY,
            "blockNumber": "0x10",
            "blockHash": BLOCK,
        },
        "eth_getTransactionByHash": {
            "from": DEPLOYER,
            "to": None,
            "input": tx_input or BYTECODE + encode(APPROVERS),
        },
        "eth_getCode": "0x6080",
    }

    def rpc(method, params):
        if method == "eth_getBlockByNumber":
            return {"hash": GENESIS if params[0] == "0x0" else BLOCK}
        return answers[method]

    return rpc


def contracts(tmp_path, abi=ABI, bytecode=BYTECODE):
    artifact = tmp_path / "out/OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({"abi": abi, "bytecode": {"object": bytecode}}))
    (tmp_path / "src").mkdir()
    (tmp_path / "src/OriginProofWalletRegistry.sol").write_text("")
    return tmp_path


def test_manifest_records_identity_roles_and_model_labels(tmp_path):
    manifest = wrapper.build_manifest(
        fake_rpc(), chain_target("sepolia"), contracts(tmp_path), TX, APPROVERS, SHA
    )

    entry = manifest["contracts"]["OriginProofWalletRegistry"]
    assert manifest["chain_id"] == 11155111
    assert manifest["chain_target"] == "sepolia"
    assert manifest["deployment_block"] == 16
    assert manifest["deployment_block_hash"] == BLOCK
    assert manifest["genesis_block_hash"] == GENESIS
    assert manifest["source_commit_sha"] == SHA
    assert entry["address"] == REGISTRY
    assert entry["deployment_tx"] == TX
    assert entry["constructor_arguments"] == [APPROVERS]
    abi_bytes = (json.dumps(ABI, indent=2) + "\n").encode()
    assert entry["abi_sha256"] == hashlib.sha256(abi_bytes).hexdigest()
    assert manifest["deployer"] == DEPLOYER
    assert manifest["roles"] == dict(
        zip(["approver_1", "approver_2", "approver_3"], APPROVERS, strict=True)
    )
    assert manifest["role_labels"]["approver_1"]["label"] == (
        "승인 노드 #1 공공·도메인 검증원(KISA 모델)"
    )
    assert manifest["role_labels"]["approver_2"]["label"] == (
        "승인 노드 #2 금융·산업 자율규제원(금융보안원 모델)"
    )
    assert manifest["role_labels"]["approver_3"]["label"] == "승인 노드 #3 통신·인프라 보안컨소시엄"
    assert {node["notice"] for node in manifest["role_labels"].values()} == {"모델(실제 기관 아님)"}
    identity = {
        key: manifest[key]
        for key in (
            "chain_id",
            "genesis_block_hash",
            "deployment_block",
            "deployment_block_hash",
            "source_commit_sha",
            "contracts",
        )
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert manifest["deployment_id"] == "dep_" + digest


@pytest.mark.parametrize(
    ("rpc", "message"),
    [
        (fake_rpc(chain_id=31337), "does not match CHAIN_TARGET=sepolia"),
        (fake_rpc(status="0x0"), "missing or failed"),
        (fake_rpc(tx_input="0x6080" + "00" * 96), "does not match the local Registry artifact"),
    ],
)
def test_manifest_rejects_wrong_chain_failed_or_foreign_deployment(tmp_path, rpc, message):
    with pytest.raises(ValueError, match=message):
        wrapper.build_manifest(
            rpc, chain_target("sepolia"), contracts(tmp_path), TX, APPROVERS, SHA
        )


def test_wrapper_requires_merged_b_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAIN_TARGET", "anvil")
    monkeypatch.delenv("CHAIN_RPC_URL", raising=False)
    for name, value in approver_env().items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=r"B PR\(#64/#68/#69/#78/#79\) must be merged first"):
        wrapper.main(["--contracts-dir", str(tmp_path), "--unlocked", "--sender", DEPLOYER])


def test_wrapper_never_overwrites_a_sepolia_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAIN_RPC_URL", "https://rpc.example/key-secret")
    for name, value in approver_env().items():
        monkeypatch.setenv(name, value)
    contracts(tmp_path)
    (tmp_path / "deployments").mkdir()
    (tmp_path / "deployments/11155111.wallet.json").write_text("{}")

    with pytest.raises(ValueError, match="refusing to overwrite") as error:
        wrapper.main(["--chain-target", "sepolia", "--contracts-dir", str(tmp_path)])

    assert "key-secret" not in str(error.value)


CHANGED_ONE_ARGUMENT = [APPROVERS[0], "0x" + "66" * 20, APPROVERS[2]]
MISMATCHED_INPUTS = {
    # Same approver arguments, different creation bytecode: a suffix check would accept this.
    "other-bytecode": OTHER_BYTECODE + encode(APPROVERS),
    # Same bytecode, exactly one constructor argument differs.
    "one-argument": BYTECODE + encode(CHANGED_ONE_ARGUMENT),
    # The expected input is only a prefix: trailing bytes must not pass.
    "trailing-bytes": BYTECODE + encode(APPROVERS) + "00" * 32,
    # Bytecode prefix is identical but truncated before the arguments.
    "truncated": BYTECODE + encode(APPROVERS)[:-2],
}


def run_wrapper(tmp_path, monkeypatch, *, browser, tx_input=None, abi=ABI):
    contracts_dir = contracts(tmp_path, abi=abi)
    for name, value in approver_env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("CHAIN_RPC_URL", "https://rpc.example/key-secret")
    monkeypatch.setattr(wrapper, "rpc_caller", lambda url: fake_rpc(tx_input=tx_input))
    forged = []
    monkeypatch.setattr(wrapper, "run_forge", lambda *args: forged.append(args) or TX)
    path_args = ["--deployment-tx", TX] if browser else ["--account", "deployer"]
    argv = ["--chain-target", "sepolia", "--contracts-dir", str(contracts_dir)]
    argv += ["--source-commit-sha", SHA, *path_args]
    output = contracts_dir / "deployments/11155111.wallet.json"
    try:
        return wrapper.main(argv), output, forged
    finally:
        # Browser recording never broadcasts; the general path broadcasts exactly once.
        assert len(forged) == (0 if browser else 1)


@pytest.mark.parametrize("browser", [False, True], ids=["forge-broadcast", "browser-record"])
def test_matching_deployment_input_writes_manifest(tmp_path, monkeypatch, browser):
    written, output, _ = run_wrapper(tmp_path, monkeypatch, browser=browser)

    assert written == output
    manifest = json.loads(output.read_text())
    assert manifest["contracts"]["OriginProofWalletRegistry"]["deployment_tx"] == TX
    assert manifest["contracts"]["OriginProofWalletRegistry"]["constructor_arguments"] == [
        APPROVERS
    ]


@pytest.mark.parametrize("browser", [False, True], ids=["forge-broadcast", "browser-record"])
@pytest.mark.parametrize("case", sorted(MISMATCHED_INPUTS))
def test_mismatched_deployment_input_is_rejected_without_manifest(
    tmp_path, monkeypatch, browser, case
):
    output = tmp_path / "deployments/11155111.wallet.json"
    with pytest.raises(ValueError, match="does not match the local Registry artifact") as error:
        run_wrapper(tmp_path, monkeypatch, browser=browser, tx_input=MISMATCHED_INPUTS[case])

    assert not output.exists()
    assert "key-secret" not in str(error.value)


@pytest.mark.parametrize(
    ("artifact", "message"),
    [
        ({"abi": ABI, "bytecode": {"object": "0x"}}, "no linked creation bytecode"),
        (
            {"abi": ABI, "bytecode": {"object": "0x6080__$abcdef$__"}},
            "no linked creation bytecode",
        ),
        ({"abi": ABI[1:], "bytecode": {"object": BYTECODE}}, "constructor is not"),
        (
            {
                "abi": [ABI[0] | {"inputs": [{"name": "a", "type": "address[]"}]}],
                "bytecode": {"object": BYTECODE},
            },
            "constructor is not",
        ),
    ],
)
def test_unusable_artifact_is_rejected_before_rpc(tmp_path, artifact, message):
    def no_rpc(method, params):
        raise AssertionError("RPC must not be called")

    path = tmp_path / "out/OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(artifact))

    with pytest.raises(ValueError, match=message):
        wrapper.build_manifest(no_rpc, chain_target("sepolia"), tmp_path, TX, APPROVERS, SHA)


def test_missing_artifact_is_rejected_before_rpc(tmp_path):
    with pytest.raises(ValueError, match="missing compiled artifact"):
        wrapper.build_manifest(None, chain_target("sepolia"), tmp_path, TX, APPROVERS, SHA)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        (
            {"SEPOLIA_RPC_URL": "https://alias.example/key-secret"},
            "https://alias.example/key-secret",
        ),
        (
            {
                "CHAIN_RPC_URL": "https://chain.example/key-secret",
                "SEPOLIA_RPC_URL": "https://alias.example/key-secret",
            },
            "https://chain.example/key-secret",
        ),
    ],
)
def test_sepolia_rpc_url_comes_from_environment_only(tmp_path, monkeypatch, env, expected):
    contracts_dir = contracts(tmp_path)
    for name, value in approver_env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("CHAIN_RPC_URL", raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    used = []
    monkeypatch.setattr(wrapper, "rpc_caller", lambda url: used.append(url) or fake_rpc())

    wrapper.main(
        ["--chain-target", "sepolia", "--contracts-dir", str(contracts_dir)]
        + ["--source-commit-sha", SHA, "--deployment-tx", TX]
    )

    assert used == [expected]


def test_anvil_ignores_sepolia_rpc_url(tmp_path, monkeypatch):
    contracts_dir = contracts(tmp_path)
    for name, value in approver_env().items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("CHAIN_RPC_URL", raising=False)
    monkeypatch.setenv("SEPOLIA_RPC_URL", "https://alias.example/key-secret")
    used = []
    monkeypatch.setattr(
        wrapper, "rpc_caller", lambda url: used.append(url) or fake_rpc(chain_id=31337)
    )

    wrapper.main(
        ["--chain-target", "anvil", "--contracts-dir", str(contracts_dir)]
        + ["--source-commit-sha", SHA, "--deployment-tx", TX]
    )

    assert used == ["http://127.0.0.1:8545"]
