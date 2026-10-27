import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain import reader as reader_module
from originproof_api import projection
from originproof_api.main import (
    UnavailableBlockchainReader,
    configured_blockchain_reader,
    create_app,
)
from originproof_api.settings import Settings
from originproof_api.wallet_runtime import WalletRuntime
from originproof_core import VerificationService
from pydantic import ValidationError

SEPOLIA_PRIMARY = "https://primary.example/v2/key-secret"
SEPOLIA_FALLBACK = "https://fallback.example/key-secret"
LABELS = [
    "승인 노드 #1 공공·도메인 검증원(KISA 모델)",
    "승인 노드 #2 금융·산업 자율규제원(금융보안원 모델)",
    "승인 노드 #3 통신·인프라 보안컨소시엄",
]


@pytest.fixture(autouse=True)
def clean_chain_env(monkeypatch):
    for name in (
        "CHAIN_TARGET",
        "API_BLOCKCHAIN_CHAIN_ID",
        "API_BLOCKCHAIN_RPC_URL",
        "API_BLOCKCHAIN_RPC_FALLBACK_URL",
        "API_WALLET_MANIFEST_PATH",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_target_is_anvil():
    settings = Settings(_env_file=None)

    assert settings.chain_target == "anvil"
    assert settings.blockchain_chain_id == 31337
    assert settings.wallet_manifest_path.endswith(
        "packages/contracts/deployments/31337.wallet.local.json"
    )
    assert settings.blockchain_rpc_urls == ()


def test_sepolia_switch_selects_chain_manifest_and_dual_rpc(monkeypatch):
    monkeypatch.setenv("CHAIN_TARGET", "sepolia")
    monkeypatch.setenv("API_BLOCKCHAIN_RPC_URL", SEPOLIA_PRIMARY)
    monkeypatch.setenv("API_BLOCKCHAIN_RPC_FALLBACK_URL", SEPOLIA_FALLBACK)
    settings = Settings(_env_file=None)

    assert settings.chain_target == "sepolia"
    assert settings.blockchain_chain_id == 11155111
    assert settings.wallet_manifest_path.endswith("deployments/11155111.wallet.json")
    assert settings.blockchain_rpc_urls == (SEPOLIA_PRIMARY, SEPOLIA_FALLBACK)
    assert "key-secret" not in repr(settings)


def test_explicit_manifest_override_is_kept():
    settings = Settings(_env_file=None, wallet_manifest_path="/tmp/custom.json")

    assert settings.wallet_manifest_path == "/tmp/custom.json"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"CHAIN_TARGET": "mainnet"}, "CHAIN_TARGET must be one of: anvil, sepolia"),
        ({"CHAIN_TARGET": "Sepolia"}, "CHAIN_TARGET must be one of"),
        ({"CHAIN_TARGET": ""}, "CHAIN_TARGET must be one of"),
        ({"CHAIN_TARGET": "sepolia"}, "CHAIN_TARGET=sepolia requires a primary RPC URL"),
        (
            {
                "CHAIN_TARGET": "sepolia",
                "API_BLOCKCHAIN_RPC_URL": "http://plain.example/key-secret",
            },
            "requires an https primary RPC URL",
        ),
        (
            {
                "CHAIN_TARGET": "sepolia",
                "API_BLOCKCHAIN_RPC_URL": SEPOLIA_PRIMARY,
                "API_BLOCKCHAIN_CHAIN_ID": "31337",
            },
            "API_BLOCKCHAIN_CHAIN_ID conflicts with CHAIN_TARGET=sepolia",
        ),
        (
            {"API_BLOCKCHAIN_RPC_URL": "https://remote.example/key-secret"},
            "CHAIN_TARGET=anvil requires a local primary RPC URL",
        ),
        (
            {
                "CHAIN_TARGET": "sepolia",
                "API_BLOCKCHAIN_RPC_URL": SEPOLIA_PRIMARY,
                "API_BLOCKCHAIN_RPC_FALLBACK_URL": SEPOLIA_PRIMARY,
            },
            "fallback RPC URL must differ from the primary",
        ),
    ],
)
def test_invalid_network_configuration_fails_clearly(monkeypatch, values, message):
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)

    assert message in str(error.value)
    assert "key-secret" not in str(error.value)


async def test_network_metadata_lists_model_approver_labels(monkeypatch):
    monkeypatch.setenv("CHAIN_TARGET", "sepolia")
    monkeypatch.setenv("API_BLOCKCHAIN_RPC_URL", SEPOLIA_PRIMARY)
    monkeypatch.setenv("API_BLOCKCHAIN_RPC_FALLBACK_URL", SEPOLIA_FALLBACK)
    test_app = create_app(
        VerificationService(None, UnavailableBlockchainReader()),
        settings=Settings(_env_file=None),
    )
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/v1/chain/network")

    assert response.status_code == 200
    body = response.json()
    assert body["chain_target"] == "sepolia"
    assert body["chain_id"] == 11155111
    assert body["rpc_fallback_configured"] is True
    assert [node["role"] for node in body["approver_nodes"]] == [
        "approver_1",
        "approver_2",
        "approver_3",
    ]
    assert [node["label"] for node in body["approver_nodes"]] == LABELS
    assert {node["notice"] for node in body["approver_nodes"]} == {"모델(실제 기관 아님)"}
    assert "key-secret" not in response.text
    assert "manifest" not in response.text


# --- CHAIN_TARGET reaches the real consumers (Reader factory, projection, wallet domain) ---

TARGETS = {
    "anvil": {
        "chain_id": 31337,
        "primary": "http://127.0.0.1:8545",
        "fallback": "http://localhost:8546",
        "manifest": "31337.wallet.local.json",
    },
    "sepolia": {
        "chain_id": 11155111,
        "primary": SEPOLIA_PRIMARY,
        "fallback": SEPOLIA_FALLBACK,
        "manifest": "11155111.wallet.json",
    },
}
GENESIS = {31337: "0x" + "a1" * 32, 11155111: "0x" + "b1" * 32}
DEPLOYED = {31337: "0x" + "a2" * 32, 11155111: "0x" + "b2" * 32}


def legacy_manifest(tmp_path, chain_id):
    path = tmp_path / f"{chain_id}.legacy.json"
    path.write_text(
        json.dumps(
            {
                "chain_id": chain_id,
                "genesis_block_hash": GENESIS[chain_id],
                "deployment_id": "dep_" + f"{chain_id:064x}",
                "deployment_block": 1,
                "deployment_block_hash": DEPLOYED[chain_id],
                "source_commit_sha": "d" * 40,
                "contracts": {
                    "IssuerRegistry": {
                        "address": "0x" + "11" * 20,
                        "constructor_arguments": ["0x" + "33" * 20],
                        "abi_sha256": "1" * 64,
                    },
                    "IssuerKeyRegistry": {
                        "address": "0x" + "22" * 20,
                        "constructor_arguments": ["0x" + "33" * 20, "0x" + "11" * 20],
                        "abi_sha256": "2" * 64,
                    },
                },
                "roles": {
                    "registry_admin": "0x" + "33" * 20,
                    "issuer_manager": "0x" + "44" * 20,
                    "key_manager": "0x" + "55" * 20,
                    "issuer_account": "0x" + "66" * 20,
                },
            }
        )
    )
    return path


def chain_transport(chain_id, down, calls):
    """Fake JSON-RPC node for `chain_id`; hosts in `down` refuse connections."""

    def handle(request):
        calls.append(str(request.url))
        if request.url.host in down:
            raise httpx.ConnectError("down", request=request)
        body = json.loads(request.content)
        method, params = body["method"], body["params"]
        result = {
            "eth_chainId": hex(chain_id),
            "eth_blockNumber": "0x10",
            "eth_getCode": "0x6080",
            "eth_call": "0x" + "00" * 31 + "01",
        }.get(method)
        if method == "eth_getBlockByNumber":
            result = {"hash": GENESIS[chain_id] if params[0] == "0x0" else DEPLOYED[chain_id]}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    return httpx.MockTransport(handle)


REAL_ASYNC_CLIENT = httpx.AsyncClient


def use_transport(monkeypatch, transport):
    monkeypatch.setattr(
        reader_module.httpx, "AsyncClient", lambda *a, **k: REAL_ASYNC_CLIENT(transport=transport)
    )


def switch(monkeypatch, tmp_path, name):
    target = TARGETS[name]
    monkeypatch.setenv("CHAIN_TARGET", name)
    monkeypatch.setenv("API_BLOCKCHAIN_RPC_URL", target["primary"])
    monkeypatch.setenv("API_BLOCKCHAIN_RPC_FALLBACK_URL", target["fallback"])
    monkeypatch.setenv(
        "API_BLOCKCHAIN_MANIFEST_PATH", str(legacy_manifest(tmp_path, target["chain_id"]))
    )
    return Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite://",
        wallet_registry_address="0x" + "77" * 20,
    )


@pytest.mark.parametrize("order", [("anvil", "sepolia"), ("sepolia", "anvil")])
async def test_switch_moves_real_consumers_in_both_directions(monkeypatch, tmp_path, order):
    for name in order:
        target = TARGETS[name]
        settings = switch(monkeypatch, tmp_path, name)
        primary_host = httpx.URL(target["primary"]).host
        calls = []
        use_transport(monkeypatch, chain_transport(target["chain_id"], {primary_host}, calls))

        # Settings-level selection (wallet manifest path is not consumed yet: B-C01 pending).
        assert settings.blockchain_chain_id == target["chain_id"]
        assert settings.wallet_manifest_path.endswith("deployments/" + target["manifest"])

        # Reader factory used by verification, readiness and /v1 lookups.
        reader = configured_blockchain_reader(settings)
        assert isinstance(reader, reader_module.JsonRpcBlockchainReader)
        assert reader._urls == (target["primary"], target["fallback"])
        assert reader._chain_id == target["chain_id"]
        assert reader.deployment_id == "dep_" + f"{target['chain_id']:064x}"
        issuer = await reader.get_issuer(settings.blockchain_issuer_id)
        assert issuer is not None and issuer.status == "ACTIVE"
        # Primary refused, the whole read was redone on the fallback.
        assert calls[0].startswith(target["primary"])
        assert all(call.startswith(target["fallback"]) for call in calls[1:])

        # Projection picks the first RPC that passes Reader identity checks.
        manifest = projection.load_manifest(
            settings.blockchain_manifest_path, settings.blockchain_chain_id
        )
        assert await projection.verified_rpc_url(settings, manifest) == target["fallback"]

        # Wallet EIP-712 domain chain ID follows the target.
        assert WalletRuntime(None, settings).domain.chain_id == str(target["chain_id"])


@pytest.mark.parametrize(("name", "other"), [("anvil", "sepolia"), ("sepolia", "anvil")])
async def test_wrong_chain_on_every_rpc_is_unavailable(monkeypatch, tmp_path, name, other):
    settings = switch(monkeypatch, tmp_path, name)
    # Both RPCs answer for the other network: identity checks fail closed on each URL.
    calls = []
    use_transport(monkeypatch, chain_transport(TARGETS[other]["chain_id"], set(), calls))

    with pytest.raises(projection.DependencyUnavailableError):
        await configured_blockchain_reader(settings).get_issuer(settings.blockchain_issuer_id)
    manifest = projection.load_manifest(
        settings.blockchain_manifest_path, settings.blockchain_chain_id
    )
    with pytest.raises(projection.DependencyUnavailableError):
        await projection.verified_rpc_url(settings, manifest)
    assert any(call.startswith(TARGETS[name]["fallback"]) for call in calls)


@pytest.mark.parametrize(("name", "other"), [("anvil", "sepolia"), ("sepolia", "anvil")])
def test_manifest_from_other_target_disables_reader(monkeypatch, tmp_path, name, other):
    switch(monkeypatch, tmp_path, name)
    monkeypatch.setenv(
        "API_BLOCKCHAIN_MANIFEST_PATH",
        str(legacy_manifest(tmp_path, TARGETS[other]["chain_id"])),
    )
    settings = Settings(_env_file=None, database_url="sqlite+aiosqlite://")

    assert isinstance(configured_blockchain_reader(settings), UnavailableBlockchainReader)
