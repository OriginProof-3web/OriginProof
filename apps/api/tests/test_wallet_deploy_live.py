"""Opt-in: deploy the wallet Registry to a disposable Anvil through the real wrapper.

Checks the #89 review point end to end: `forge script --broadcast` must record exactly one
CREATE for OriginProofWalletRegistry in run-latest.json, and deploy_wallet_registry.py must
write a manifest whose address, transaction and block match the chain. Run with
ORIGINPROOF_WALLET_LIVE=1 (needs anvil and forge on PATH and a built contracts tree).
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

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


async def connect(manifest_path, address, urls):
    from infrastructure.blockchain.wallet_deployment import WalletRegistryConnector

    settings = SimpleNamespace(
        wallet_manifest_path=str(manifest_path),
        blockchain_chain_id=31337,
        wallet_registry_address=address,
        blockchain_rpc_urls=urls,
    )
    async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
        connector = WalletRegistryConnector(client, settings)
        adapter = await connector()
        if adapter is None:
            return None, "absent"
        # 등록되지 않은 기관은 None(가짜 값 없음) — 실제 체인 읽기까지 확인
        return connector.rpc_index, await adapter.issuer("0x" + "ab" * 32)


async def app_lifespan(monkeypatch, manifest_path, address, url):
    from originproof_api import main
    from originproof_api.settings import Settings

    async def no_cleanup(app, restart):
        return []

    async def no_maintenance(app, stop):
        await stop.wait()

    # DB 정리·유지 작업만 끄고(이 검사는 DB 없음) 지갑 연결 경로는 실제 코드 그대로 실행
    monkeypatch.setattr(main, "cleanup", no_cleanup)
    monkeypatch.setattr(main, "maintenance", no_maintenance)
    settings = Settings(
        _env_file=None,
        chain_target="anvil",
        blockchain_rpc_url=url,
        wallet_registry_address=address,
        wallet_manifest_path=str(manifest_path),
    )
    app = main.create_app(settings=settings)
    async with app.router.lifespan_context(app):
        runtime = app.state.wallet_runtime
        assert runtime.chain is not None and runtime.connect.rpc_index == 0
        found = await runtime.rpc("issuer", "0x" + "ab" * 32)
    assert runtime.connect.client.is_closed
    return found


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

        # API 생산 연결: 배포 기록으로 체인 위 배포를 검증한 뒤 주입되는지,
        # 주 RPC 장애면 보조로 붙는지
        assert manifest["runtime_code_hash"].startswith("0x")
        assert manifest["creation_bytecode"].startswith("0x")
        dead = "http://127.0.0.1:1"
        result = asyncio.run(connect(output, entry["address"], (dead, url)))
        assert result == (1, None)
        # 실제 API 시작 경로(create_app lifespan): 설정만으로 배포 기록을 읽어 스스로 연결
        assert asyncio.run(app_lifespan(monkeypatch, output, entry["address"], url)) is None
        # 배포 기록 위조(런타임 코드 해시 변경)면 연결하지 않고 503 상태로 남음
        forged = Path(output).with_name("forged.wallet.json")
        bad = dict(manifest, runtime_code_hash="0x" + "00" * 32)
        forged.write_text(json.dumps(bad))
        try:
            assert asyncio.run(connect(forged, entry["address"], (url,))) == (None, "absent")
        finally:
            forged.unlink(missing_ok=True)
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
