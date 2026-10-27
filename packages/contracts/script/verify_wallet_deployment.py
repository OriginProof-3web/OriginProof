"""Read-only deployment/constructor verification; RPC credentials stay in the environment."""

import asyncio
import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
from eth_utils import keccak
from infrastructure.blockchain.wallet_creation import verified_approvers
from infrastructure.blockchain.wallet_deployment import load_wallet_deployment
from infrastructure.blockchain.wallet_rpc import WalletRpc

ROOT = Path(__file__).resolve().parents[3]
READ_METHODS = {
    "eth_chainId", "eth_getBlockByNumber", "eth_getCode",
    "eth_getTransactionByHash", "eth_getTransactionReceipt",
}


async def verify():
    manifest_path = ROOT / "packages/contracts/deployments/11155111.wallet.json"
    manifest = json.loads(manifest_path.read_text())
    contract = manifest["contracts"]["OriginProofWalletRegistry"]
    artifact_path = ROOT / (
        "packages/contracts/out/OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json"
    )
    artifact = json.loads(artifact_path.read_text())
    if artifact["bytecode"]["object"].lower() != manifest["creation_bytecode"].lower():
        raise ValueError("local build differs from the committed deployment")
    deployment, proof = load_wallet_deployment(
        manifest_path, chain_id=11155111, address=contract["address"]
    )
    trace = []

    async def request(req):
        if json.loads(req.content)["method"] not in READ_METHODS:
            raise ValueError("read-only RPC method required")

    async def response(res):
        await res.aread()
        body = res.json()
        trace.append({
            "method": json.loads(res.request.content)["method"],
            "http_status": res.status_code,
            "rpc_error_code": (body.get("error") or {}).get("code"),
        })

    result = {
        "date_utc": datetime.now(UTC).isoformat(),
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python": platform.python_version(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "local_creation_bytecode_matches_manifest": True,
        "creation_bytecode_keccak": "0x" + keccak(proof.creation_bytecode).hex(),
        "chain_id": 11155111,
        "registry": contract["address"],
        "deployment_tx": proof.tx_hash,
        "deployment_block": manifest["deployment_block"],
        "deployment_block_hash": manifest["deployment_block_hash"],
        "runtime_code_hash": manifest["runtime_code_hash"],
        "attempts": [], "writes": 0, "service_api_calls": 0,
    }
    async with httpx.AsyncClient(
        timeout=15, trust_env=False,
        event_hooks={"request": [request], "response": [response]},
    ) as client:
        rpc = WalletRpc(client, os.environ["SEPOLIA_RPC_URL"], **deployment)
        for _ in range(3):
            start = len(trace)
            try:
                genesis = await rpc.block("0x0")
                if genesis["hash"] != manifest["genesis_block_hash"]:
                    raise ValueError("genesis mismatch")
                approvers = await verified_approvers(rpc, proof)
                expected = [a.lower() for a in contract["constructor_arguments"][0]]
                if list(approvers) != expected:
                    raise ValueError("constructor approver mismatch")
                head = await rpc.snapshot()
                attempt = {
                    "status": "PASS", "head_number": int(head["number"], 16),
                    "head_hash": head["hash"], "approvers": list(approvers),
                }
            except Exception as exc:  # report type only: exception messages can contain RPC keys
                attempt = {"status": "FAIL", "exception_type": type(exc).__name__}
            attempt["rpc_calls"] = trace[start:]
            result["attempts"].append(attempt)
            if attempt["status"] == "FAIL":
                break
    print(json.dumps(result, indent=2))
    return len(result["attempts"]) == 3 and all(
        a["status"] == "PASS" for a in result["attempts"]
    )


if __name__ == "__main__":
    try:
        success = asyncio.run(verify())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "exception_type": type(exc).__name__}))
        success = False
    raise SystemExit(0 if success else 1)
