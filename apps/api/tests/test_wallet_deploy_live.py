"""Opt-in: deploy the wallet Registry to a disposable Anvil through the real wrapper.

Checks the #89 review point end to end: `forge script --broadcast` must record exactly one
CREATE for OriginProofWalletRegistry in run-latest.json, and deploy_wallet_registry.py must
write a manifest whose address, transaction and block match the chain. Run with
ORIGINPROOF_WALLET_LIVE=1 (needs anvil and forge on PATH and a built contracts tree).
"""

import json
import os
import shutil
import socket
import subprocess
import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"
SCRIPT = "DeployWalletRegistry.s.sol"
MANIFEST = CONTRACTS / "deployments/31337.wallet.local.json"
# Anvil's default unlocked account 0 deploys; approvers are Anvil accounts 1-3 (public test keys).
DEPLOYER = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
APPROVERS = [
    "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    "0x90F79bf6EB2c4f870c6CC86b2b6b6b6b6b6b6b6b",
]

pytestmark = pytest.mark.skipif(
    os.environ.get("ORIGINPROOF_WALLET_LIVE") != "1",
    reason="disposable wallet EVM opt-in",
)


def load_wrapper():
    spec = spec_from_file_location(
        "deploy_wallet_registry", CONTRACTS / "script/deploy_wallet_registry.py"
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rpc(url, method, params):
    response = httpx.post(
        url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=5
    )
    response.raise_for_status()
    return response.json()["result"]


def test_broadcast_records_one_create_and_wrapper_writes_matching_manifest(monkeypatch):
    anvil, forge = shutil.which("anvil"), shutil.which("forge")
    if anvil is None or forge is None:
        pytest.fail("ORIGINPROOF_WALLET_LIVE=1 requires anvil and forge on PATH")
    subprocess.run([forge, "build"], cwd=CONTRACTS, check=True, capture_output=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [anvil, "--host", "127.0.0.1", "--port", str(port), "--chain-id", "31337", "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # The wrapper writes the developer's local manifest path; keep any existing one intact.
    saved = MANIFEST.read_bytes() if MANIFEST.exists() else None
    try:
        for _ in range(50):
            try:
                rpc(url, "eth_chainId", [])
                break
            except httpx.HTTPError:
                time.sleep(0.1)
        monkeypatch.setenv("CHAIN_RPC_URL", url)
        for i, address in enumerate(APPROVERS, 1):
            monkeypatch.setenv(f"WALLET_APPROVER_{i}_ADDRESS", address)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

        output = load_wrapper().main(
            [
                "--chain-target",
                "anvil",
                "--unlocked",
                "--sender",
                DEPLOYER,
                "--source-commit-sha",
                sha,
            ]
        )

        broadcast = json.loads(
            (CONTRACTS / f"broadcast/{SCRIPT}/31337/run-latest.json").read_text()
        )
        creates = [t for t in broadcast["transactions"] if t.get("transactionType") == "CREATE"]
        assert len(creates) == 1
        assert creates[0]["contractName"] == "OriginProofWalletRegistry"

        manifest = json.loads(Path(output).read_text())
        entry = manifest["contracts"]["OriginProofWalletRegistry"]
        assert manifest["chain_id"] == 31337
        assert manifest["source_commit_sha"] == sha
        assert entry["address"].lower() == creates[0]["contractAddress"].lower()
        assert entry["deployment_tx"] == creates[0]["hash"]
        assert entry["constructor_arguments"] == [APPROVERS]
        receipt = rpc(url, "eth_getTransactionReceipt", [entry["deployment_tx"]])
        assert receipt["status"] == "0x1"
        assert int(receipt["blockNumber"], 16) == manifest["deployment_block"]
        assert receipt["contractAddress"].lower() == entry["address"].lower()
        assert rpc(url, "eth_getCode", [entry["address"], "latest"]) not in ("0x", "0x0")
    finally:
        process.terminate()
        try:
            process.wait(5)
        except subprocess.TimeoutExpired:
            process.kill()
        if saved is None:
            MANIFEST.unlink(missing_ok=True)
        else:
            MANIFEST.write_bytes(saved)
