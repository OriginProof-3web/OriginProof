"""Local-only deployment using an unlocked development account; never reads private keys."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"


def export_abi(forge: str) -> None:
    subprocess.run([forge, "build"], cwd=CONTRACTS, check=True, capture_output=True)
    for name in ("IssuerRegistry", "IssuerKeyRegistry"):
        artifact = json.loads((CONTRACTS / f"out/{name}.sol/{name}.json").read_text())
        target = CONTRACTS / f"abi/{name}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(artifact["abi"], indent=2) + "\n")


def deploy(rpc_url: str, signer: str) -> Path:
    from infrastructure.blockchain.reader import address

    if urlparse(rpc_url).hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("only loopback RPC is supported")
    address(signer)
    forge = shutil.which("forge")
    if forge is None:
        raise ValueError("forge must be on PATH")
    with httpx.Client(timeout=10, trust_env=False) as client:

        def rpc(method, params):
            response = client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params,
                },
            )
            response.raise_for_status()
            body = response.json()
            if "error" in body:
                raise ValueError("local RPC failure")
            return body["result"]

        if int(rpc("eth_chainId", []), 16) != 31337:
            raise ValueError("chain ID must be 31337")
        admin = address(rpc("eth_accounts", [])[0])
        golden = json.loads(
            (ROOT / "fixtures/golden/card_payment_notice_signing_v1.json").read_text()
        )
        start = int(
            datetime.fromisoformat(
                golden["signing_payload"]["issued_at"].replace("Z", "+00:00")
            ).timestamp()
        )
        env = os.environ | {
            "CHAIN_DEPLOYER_ADDRESS": admin,
            "CHAIN_MOCK_SIGNER_ADDRESS": signer,
            "CHAIN_KEY_VALID_FROM": str(start),
            "CHAIN_KEY_VALID_UNTIL": str(start + 365 * 86400),
        }
        subprocess.run(
            [
                forge,
                "script",
                "script/DeployLocal.s.sol:DeployLocal",
                "--rpc-url",
                rpc_url,
                "--broadcast",
                "--unlocked",
                "--sender",
                admin,
            ],
            cwd=CONTRACTS,
            env=env,
            check=True,
            capture_output=True,
        )
        export_abi(forge)
        broadcast = json.loads(
            (CONTRACTS / "broadcast/DeployLocal.s.sol/31337/run-latest.json").read_text()
        )
        contracts, blocks = {}, []
        for tx in broadcast["transactions"]:
            name = tx.get("contractName")
            if tx.get("transactionType") != "CREATE" or name not in (
                "IssuerRegistry",
                "IssuerKeyRegistry",
            ):
                continue
            contract_address = address(tx["contractAddress"])
            receipt = rpc("eth_getTransactionReceipt", [tx["hash"]])
            if int(receipt["status"], 16) != 1:
                raise ValueError("deployment transaction failed")
            blocks.append(int(receipt["blockNumber"], 16))
            contracts[name] = {"address": contract_address}
        if len(contracts) != 2:
            raise ValueError("missing deployed registry")
        contracts["IssuerRegistry"]["constructor_arguments"] = [admin]
        contracts["IssuerKeyRegistry"]["constructor_arguments"] = [
            admin,
            contracts["IssuerRegistry"]["address"],
        ]
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        manifest = {
            "chain_id": 31337,
            "deployment_block": min(blocks),
            "source_commit_sha": sha,
            "contracts": contracts,
        }
        target = CONTRACTS / "deployments/31337.local.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2) + "\n")
        return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc-url", default="http://127.0.0.1:8545")
    parser.add_argument("--signer", required=True, help="Public signer address from the M1 seed")
    args = parser.parse_args()
    print(deploy(args.rpc_url, args.signer).relative_to(ROOT))
