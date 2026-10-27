"""Wallet Registry deploy wrapper for CHAIN_TARGET=anvil|sepolia; never reads or prints keys.

Run only after B PR(#64/#68/#69/#78/#79) is merged: it deploys B's OriginProofWalletRegistry
(Governance is inherited) through script/DeployWalletRegistry.s.sol and records
deployments/<chainId>.wallet[.local].json in the current manifest shape (deployment ID, block/hash,
genesis, tx hash, ABI hash, roles). Signing is chosen on the CLI: --account (keystore, or the
ETH_KEYSTORE_ACCOUNT env), --ledger, --trezor, or --unlocked --sender on Anvil only. A browser
wallet deployment is recorded afterwards with --deployment-tx. On both paths the transaction input
must equal the local forge artifact's creation bytecode plus the ABI-encoded constructor arguments
byte for byte, or no manifest is written. The RPC URL is read from the
CHAIN_RPC_URL environment variable (or SEPOLIA_RPC_URL for sepolia), passed to forge through the
environment and never printed or put on a command line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import httpx
from eth_utils import keccak
from infrastructure.blockchain.manifest import validate_address, validate_hash
from infrastructure.blockchain.network import APPROVER_NODES, chain_target, rpc_urls

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"
NAME = "OriginProofWalletRegistry"
SCRIPT = "DeployWalletRegistry.s.sol"
B_PENDING = "B PR(#64/#68/#69/#78/#79) must be merged first: missing src/" + NAME + ".sol"


def approvers(env) -> list[str]:
    values = [validate_address(env.get(f"WALLET_APPROVER_{index}_ADDRESS")) for index in (1, 2, 3)]
    if len({value.lower() for value in values}) != 3:
        raise ValueError("approver addresses must be distinct")
    return values


def signer_args(args, target) -> list[str]:
    modes = [args.account is not None, args.ledger, args.trezor, args.unlocked]
    if sum(modes) > 1:
        raise ValueError("choose one signer: --account, --ledger, --trezor or --unlocked")
    if args.unlocked and target.name != "anvil":
        raise ValueError("--unlocked is only allowed for CHAIN_TARGET=anvil")
    if args.unlocked and not args.sender:
        raise ValueError("--unlocked requires --sender")
    if not any(modes) and not os.environ.get("ETH_KEYSTORE_ACCOUNT"):
        raise ValueError("a signer is required: --account, --ledger, --trezor or --unlocked")
    result = []
    if args.account is not None:
        result += ["--account", args.account]
    for flag in ("ledger", "trezor", "unlocked"):
        if getattr(args, flag):
            result.append(f"--{flag}")
    if args.sender:
        result += ["--sender", validate_address(args.sender)]
    return result


def rpc_caller(url):
    client = httpx.Client(timeout=30, trust_env=False)

    def rpc(method, params):
        try:
            response = client.post(
                url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError):
            raise ValueError(f"RPC request failed: {method}") from None
        if "error" in body or "result" not in body:
            raise ValueError(f"RPC returned an error: {method}")
        return body["result"]

    return rpc


def run_forge(
    contracts_dir: Path, target, url: str, approver_addresses, signer: list[str], gas_multiplier=200
) -> str:
    forge = shutil.which("forge")
    if forge is None:
        raise ValueError("forge must be on PATH")
    env = os.environ | {
        "FOUNDRY_ETH_RPC_URL": url,
        "WALLET_DEPLOY_CHAIN_ID": str(target.chain_id),
    }
    env |= {f"WALLET_APPROVER_{i}_ADDRESS": a for i, a in enumerate(approver_addresses, 1)}
    # Output is not captured so keystore/hardware prompts stay interactive.
    # forge 1.8.1 로컬 모의 실행(약 2.7M gas)은 Sepolia 의 오른 코드 저장 비용을 모름.
    # 2026-10-27 실제 노드 eth_estimateGas 는 19,187,530 → 130%·200% 배포 모두 가스 부족 실패
    # (0xa11034…, 0xc98a4e…). Sepolia 는 --gas-multiplier 800 으로 보냄. 실제 사용 가스만 청구됨.
    subprocess.run(
        [
            forge,
            "script",
            f"script/{SCRIPT}:DeployWalletRegistry",
            "--broadcast",
            "--gas-estimate-multiplier",
            str(gas_multiplier),
            *signer,
        ],
        cwd=contracts_dir,
        env=env,
        check=True,
    )
    broadcast = json.loads(
        (contracts_dir / f"broadcast/{SCRIPT}/{target.chain_id}/run-latest.json").read_text()
    )
    creates = [tx for tx in broadcast["transactions"] if tx.get("transactionType") == "CREATE"]
    if len(creates) != 1:
        raise ValueError("expected exactly one CREATE transaction in the broadcast")
    return validate_hash(creates[0]["hash"])


def load_artifact(contracts_dir: Path) -> dict:
    artifact_path = contracts_dir / f"out/{NAME}.sol/{NAME}.json"
    if not artifact_path.is_file():
        raise ValueError("missing compiled artifact; run forge build first")
    return json.loads(artifact_path.read_text())


def expected_creation_input(artifact: dict, approver_addresses) -> str:
    """0x + creation bytecode + abi.encode(address[3]), exactly as DeployWalletRegistry sends."""
    bytecode = artifact.get("bytecode")
    bytecode = bytecode.get("object") if isinstance(bytecode, dict) else bytecode
    if not isinstance(bytecode, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", bytecode):
        raise ValueError("artifact has no linked creation bytecode")
    constructors = [item for item in artifact.get("abi", []) if item.get("type") == "constructor"]
    if len(constructors) != 1 or [
        item.get("type") for item in constructors[0].get("inputs", [])
    ] != ["address[3]"]:
        raise ValueError("artifact constructor is not (address[3])")
    if len(approver_addresses) != 3:
        raise ValueError("exactly three approvers are required")
    encoded = "".join(
        validate_address(value)[2:].lower().rjust(64, "0") for value in approver_addresses
    )
    return bytecode.lower() + encoded


def build_manifest(rpc, target, contracts_dir: Path, tx_hash: str, approver_addresses, sha):
    artifact = load_artifact(contracts_dir)
    expected_input = expected_creation_input(artifact, approver_addresses)
    if int(rpc("eth_chainId", []), 16) != target.chain_id:
        raise ValueError(f"RPC chain ID does not match CHAIN_TARGET={target.name}")
    receipt = rpc("eth_getTransactionReceipt", [tx_hash])
    if not isinstance(receipt, dict) or int(receipt["status"], 16) != 1:
        raise ValueError("deployment transaction missing or failed")
    transaction = rpc("eth_getTransactionByHash", [tx_hash])
    # Whole-input byte equality: local creation bytecode + every ABI-encoded constructor argument.
    if (
        not isinstance(transaction, dict)
        or transaction.get("to") is not None
        or not isinstance(transaction.get("input"), str)
        or transaction["input"].lower() != expected_input
    ):
        raise ValueError("deployment input does not match the local Registry artifact")
    registry = validate_address(receipt["contractAddress"])
    block = int(receipt["blockNumber"], 16)
    code = rpc("eth_getCode", [registry, hex(block)])
    if not isinstance(code, str) or code in ("0x", "0x0"):
        raise ValueError("no Registry code at the deployed address")
    genesis = rpc("eth_getBlockByNumber", ["0x0", False])
    deployed = rpc("eth_getBlockByNumber", [hex(block), False])
    if validate_hash(deployed["hash"]) != validate_hash(receipt["blockHash"]):
        raise ValueError("deployment block is no longer canonical")
    abi = (json.dumps(artifact["abi"], indent=2) + "\n").encode()
    identity = {
        "chain_id": target.chain_id,
        "genesis_block_hash": validate_hash(genesis["hash"]),
        "deployment_block": block,
        "deployment_block_hash": validate_hash(deployed["hash"]),
        "source_commit_sha": sha,
        "contracts": {
            NAME: {
                "address": registry,
                "constructor_arguments": [approver_addresses],
                "abi_sha256": hashlib.sha256(abi).hexdigest(),
                "deployment_tx": tx_hash,
            }
        },
    }
    deployment_id = (
        "dep_"
        + hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    roles = {
        node["role"]: value for node, value in zip(APPROVER_NODES, approver_addresses, strict=True)
    }
    return {
        **identity,
        "deployment_id": deployment_id,
        "chain_target": target.name,
        "deployer": validate_address(transaction["from"]),
        "roles": roles,
        "role_labels": {node["role"]: node for node in APPROVER_NODES},
        # API 주입(from_deployment)이 체인에서 다시 검증하는 값. 배포 ID 계산에는 넣지 않음.
        # runtime_code_hash: 배포 블록 실제 코드의 keccak
        # creation_bytecode: 로컬 빌드 생성 코드(생성자 인자 제외)
        "runtime_code_hash": "0x" + keccak(bytes.fromhex(code[2:])).hex(),
        "creation_bytecode": expected_input[: len(expected_input) - 64 * 3],
    }


def main(argv=None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain-target", default=os.environ.get("CHAIN_TARGET"))
    parser.add_argument("--contracts-dir", type=Path, default=CONTRACTS)
    parser.add_argument("--deployment-tx", help="record an existing browser-wallet deployment")
    parser.add_argument("--account", help="Foundry keystore account name (password prompted)")
    parser.add_argument("--ledger", action="store_true")
    parser.add_argument("--trezor", action="store_true")
    parser.add_argument("--unlocked", action="store_true", help="Anvil only, with --sender")
    parser.add_argument("--sender")
    parser.add_argument("--source-commit-sha")
    parser.add_argument(
        "--gas-multiplier", type=int, default=200, help="forge --gas-estimate-multiplier (%%)"
    )
    args = parser.parse_args(argv)

    target = chain_target(args.chain_target)
    # SEPOLIA_RPC_URL is the same variable foundry.toml's `sepolia` rpc_endpoints alias reads.
    env_url = os.environ.get("CHAIN_RPC_URL") or (
        os.environ.get("SEPOLIA_RPC_URL") if target.name == "sepolia" else None
    )
    url = rpc_urls(target, env_url)[0]
    approver_addresses = approvers(os.environ)
    contracts_dir = args.contracts_dir.resolve()
    if not (contracts_dir / f"src/{NAME}.sol").is_file():
        raise ValueError(B_PENDING)
    output = contracts_dir / "deployments" / target.wallet_manifest
    if target.name != "anvil" and output.exists():
        raise ValueError(f"refusing to overwrite an existing non-local manifest: {output.name}")
    sha = (
        args.source_commit_sha
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("invalid source commit SHA")

    if args.deployment_tx:
        tx_hash = validate_hash(args.deployment_tx)
    else:
        signer = signer_args(args, target)
        if not 100 <= args.gas_multiplier <= 2000:
            raise ValueError("--gas-multiplier must be 100..2000")
        tx_hash = run_forge(
            contracts_dir, target, url, approver_addresses, signer, args.gas_multiplier
        )
    manifest = build_manifest(
        rpc_caller(url), target, contracts_dir, tx_hash, approver_addresses, sha
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return output


if __name__ == "__main__":
    print(main())
