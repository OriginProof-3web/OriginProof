"""Wallet Registry wiring: manifest checks, RPC fallback, lazy reconnect (no chain)."""

import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from infrastructure.blockchain import wallet_deployment as wd
from infrastructure.blockchain.errors import BlockchainConfigurationError
from originproof_api.wallet_runtime import WalletRuntime

ADDRESS = "0x" + "12" * 20
TX = "0x" + "34" * 32
ABI = [{"type": "constructor", "stateMutability": "nonpayable", "inputs": []}]


def write(tmp_path, **override):
    abi = tmp_path / "abi.json"
    abi.write_text(json.dumps(ABI, indent=2) + "\n")
    manifest = {
        "chain_id": 31337,
        "deployment_block": 7,
        "deployment_block_hash": "0x" + "56" * 32,
        "runtime_code_hash": "0x" + "78" * 32,
        "creation_bytecode": "0x6080",
        "contracts": {
            wd.NAME: {
                "address": ADDRESS,
                "abi_sha256": hashlib.sha256(abi.read_bytes()).hexdigest(),
                "deployment_tx": TX,
            }
        },
    }
    manifest.update(override)
    path = tmp_path / "31337.wallet.json"
    path.write_text(json.dumps(manifest))
    return path, abi


def test_valid_manifest_becomes_deployment_and_creation_proof(tmp_path):
    path, abi = write(tmp_path)
    deployment, proof = wd.load_wallet_deployment(
        path, chain_id=31337, address=ADDRESS, abi_path=abi
    )
    assert deployment["deployment_block"] == 7
    assert deployment["runtime_code_hash"] == "0x" + "78" * 32
    assert deployment["abi"] == ABI
    assert proof.tx_hash == TX and proof.creation_bytecode == bytes.fromhex("6080")


@pytest.mark.parametrize(
    ("kwargs", "override"),
    [
        ({"chain_id": 11155111, "address": ADDRESS}, {}),
        ({"chain_id": 31337, "address": "0x" + "99" * 20}, {}),
        ({"chain_id": 31337, "address": ADDRESS}, {"runtime_code_hash": None}),
        ({"chain_id": 31337, "address": ADDRESS}, {"creation_bytecode": "6080"}),
    ],
)
def test_other_chain_address_or_missing_evidence_is_refused(tmp_path, kwargs, override):
    path, abi = write(tmp_path, **override)
    if override.get("runtime_code_hash", 1) is None:
        data = json.loads(path.read_text())
        del data["runtime_code_hash"]
        path.write_text(json.dumps(data))
    with pytest.raises(BlockchainConfigurationError):
        wd.load_wallet_deployment(path, abi_path=abi, **kwargs)


def test_changed_abi_is_refused(tmp_path):
    path, abi = write(tmp_path)
    abi.write_text("[]\n")
    with pytest.raises(BlockchainConfigurationError):
        wd.load_wallet_deployment(path, chain_id=31337, address=ADDRESS, abi_path=abi)


def settings(path, urls=("http://primary", "http://fallback")):
    return SimpleNamespace(
        wallet_manifest_path=str(path),
        blockchain_chain_id=31337,
        wallet_registry_address=ADDRESS,
        blockchain_rpc_urls=urls,
    )


def test_connector_uses_fallback_when_primary_fails_and_throttles_retries(tmp_path, monkeypatch):
    path, abi = write(tmp_path)
    monkeypatch.setattr(wd, "ABI_PATH", abi)
    tried = []

    async def fake(client, url, *, creation_proof, **deployment):
        tried.append(url)
        if url == "http://primary":
            raise RuntimeError("down")
        return "adapter"

    monkeypatch.setattr(wd.WalletRegistryReadAdapter, "from_deployment", fake)
    now = [100.0]
    connector = wd.WalletRegistryConnector(None, settings(path), clock=lambda: now[0])
    assert asyncio.run(connector()) == "adapter"
    assert tried == ["http://primary", "http://fallback"] and connector.rpc_index == 1
    # 재시도 간격 안에서는 체인에 다시 묻지 않음
    assert asyncio.run(connector()) is None and len(tried) == 2
    now[0] += wd.RETRY_SECONDS
    asyncio.run(connector())
    assert len(tried) == 4


def test_connector_leaves_api_unconnected_on_bad_manifest(tmp_path):
    connector = wd.WalletRegistryConnector(None, settings(tmp_path / "missing.json"))
    assert asyncio.run(connector()) is None


def test_runtime_reconnects_lazily_and_stays_503_until_connected():
    runtime = WalletRuntime(None, SimpleNamespace(), None)
    calls = []

    async def connect():
        calls.append(1)
        return None

    runtime.connect = connect
    with pytest.raises(HTTPException) as exc:
        asyncio.run(runtime.rpc("issuer", "0x" + "ab" * 32))
    assert exc.value.status_code == 503 and exc.value.detail == "WALLET_REGISTRY_UNAVAILABLE"
    assert calls == [1]
