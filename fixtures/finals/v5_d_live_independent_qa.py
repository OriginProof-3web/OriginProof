"""Opt-in D verification against a disposable B Registry; fixed C63 CLI, no service API/AI/DB."""

import asyncio
import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import test_v5_d_independent_verifier as pinned
from eth_abi import encode
from eth_utils import keccak
from originproof_core.canonicalization import canonical_json_bytes
from originproof_core.wallet_contract import (
    GovernanceProposal,
    KeyProofMessage,
    PublishMessage,
    RevokeMessage,
    SigningRequest,
    VerificationMaterial,
    WalletDomain,
)
from originproof_core.wallet_signatures import (
    document_id,
    identifier_hash,
    original_bytes,
    proposal_id,
    typed_data,
)

ROOT = Path(__file__).resolve().parents[2]
FOUNDRY = (
    "ghcr.io/foundry-rs/foundry:v1.4.4@sha256:"
    "9584dfbb0e2e9bda80332b66a7cebed635fc9786638871df6b7594e39e678578"
)
pytestmark = pytest.mark.skipif(
    os.environ.get("D_WALLET_INDEPENDENT_LIVE") != "1",
    reason="explicit disposable local EVM opt-in",
)


def command(*args):
    return subprocess.check_output(list(args), cwd=ROOT, stderr=subprocess.PIPE, timeout=120)


def abi_type(field):
    return (
        "(" + ",".join(abi_type(c) for c in field["components"]) + ")" + field["type"][5:]
        if field["type"].startswith("tuple")
        else field["type"]
    )


def abi_value(field, value):
    if field["type"] == "tuple":
        data = value.model_dump(by_alias=True)
        return tuple(abi_value(c, data[c["name"]]) for c in field["components"])
    if field["type"].startswith("bytes"):
        return bytes.fromhex(value[2:])
    return int(value) if field["type"].startswith("uint") else value


async def test_fixed_c63_against_actual_disposable_b_registry(tmp_path, tmp_path_factory):
    product = os.environ.get("D_WALLET_PRODUCT_SHA", "")
    assert re.fullmatch(r"[0-9a-f]{40}", product), "explicit immutable product SHA required"
    assert not command("git", "status", "--porcelain").strip(), "clean QA source required"
    qa = command("git", "rev-parse", "HEAD").decode().strip()
    image = "originproof-w5-d-qa-deployer:" + product
    revision = (
        command(
            "docker",
            "image",
            "inspect",
            image,
            "--format",
            '{{ index .Config.Labels "org.opencontainers.image.revision" }}',
        )
        .decode()
        .strip()
    )
    assert revision == product
    artifact = json.loads(
        command(
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "cat",
            image,
            "/workspace/packages/contracts/out/"
            "OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json",
        )
    )
    abi = artifact["abi"]
    expected_abi = command(
        "git", "show", f"{product}:packages/contracts/abi/OriginProofWalletRegistry.json"
    )
    assert abi == json.loads(expected_abi)
    functions = {f["name"]: f for f in abi if f["type"] == "function"}
    support = pinned.c63_support.__wrapped__(tmp_path_factory)
    name = "originproof-d-independent-" + uuid4().hex[:16]
    report = {
        "status": "FAIL",
        "scope": "ACTUAL_DISPOSABLE_LOCAL_EVM_NO_SERVICE_API_DB_BROWSER",
        "product_sha": product,
        "qa_sha": qa,
        "c63_sha": pinned.C63_SHA,
        "compiled_abi_sha256": hashlib.sha256(expected_abi).hexdigest(),
        "model_calls": 0,
        "service_api_calls": 0,
        "scenarios": [],
        "resources_closed": False,
    }
    report_path = Path(os.environ.get("D_LIVE_REPORT", str(tmp_path / "live-summary.json")))
    assert not report_path.exists(), "never overwrite evidence"
    try:
        command(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "127.0.0.1::8545",
            "--entrypoint",
            "anvil",
            FOUNDRY,
            "--host",
            "0.0.0.0",
            "--chain-id",
            "31337",
            "--silent",
            "--state",
            "/tmp/d-independent-state.json",
            "--preserve-historical-states",
        )
        port = command("docker", "port", name, "8545/tcp").decode().strip().rsplit(":", 1)[1]
        url = "http://127.0.0.1:" + port
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:

            async def rpc(method, params):
                response = await client.post(
                    url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
                )
                response.raise_for_status()
                value = response.json()
                assert "error" not in value, "local RPC rejected fixture command"
                return value["result"]

            async def ready():
                for _ in range(100):
                    try:
                        assert await rpc("eth_chainId", []) == "0x7a69"
                        return
                    except httpx.TransportError:
                        await asyncio.sleep(0.05)
                pytest.fail("owned local EVM startup failed")

            await ready()
            accounts = await rpc("eth_accounts", [])
            creation = bytes.fromhex(artifact["bytecode"]["object"].removeprefix("0x"))
            tx = await rpc(
                "eth_sendTransaction",
                [
                    {
                        "from": accounts[0],
                        "gas": "0xc00000",
                        "data": "0x" + (creation + encode(["address[3]"], [accounts[:3]])).hex(),
                    }
                ],
            )
            deployed = await rpc("eth_getTransactionReceipt", [tx])
            assert deployed["status"] == "0x1"
            address = deployed["contractAddress"]
            domain = WalletDomain(chain_id="31337", verifying_contract=address)
            report.update(
                chain_id="31337",
                registry=address,
                deployment_tx=tx,
                deployment_block=deployed["blockNumber"],
                deployment_hash=deployed["blockHash"],
            )

            async def send(function, values, sender):
                inputs = functions[function]["inputs"]
                types = [abi_type(f) for f in inputs]
                signature = function + "(" + ",".join(types) + ")"
                data = keccak(text=signature)[:4] + encode(
                    types, [abi_value(f, v) for f, v in zip(inputs, values, strict=True)]
                )
                tx_hash = await rpc(
                    "eth_sendTransaction",
                    [{"from": sender, "to": address, "gas": "0x800000", "data": "0x" + data.hex()}],
                )
                mined = await rpc("eth_getTransactionReceipt", [tx_hash])
                assert mined["status"] == "0x1", "fixture transaction must execute"
                return mined

            async def sign(message):
                return await rpc(
                    "eth_signTypedData_v4", [accounts[3], json.dumps(typed_data(domain, message))]
                )

            golden = json.loads((ROOT / "fixtures/golden/wallet_contract_v1.json").read_text())
            last_args = None
            for vector in golden["vectors"]:
                template = vector["label"]
                if template not in {"PAYMENT_REQUEST", "OFFICIAL_DOCUMENT"}:
                    continue
                stamp = int((await rpc("eth_getBlockByNumber", ["latest", False]))["timestamp"], 16)
                issuer, key = (
                    identifier_hash("D-live-" + template),
                    identifier_hash("D-key-" + template),
                )
                metadata = {"issuer_id": issuer, "name": "Synthetic", "domain": "example.invalid"}
                proposal = GovernanceProposal(
                    action=1,
                    issuer_id=issuer,
                    key_id=key,
                    signer=accounts[3],
                    metadata_hash="0x" + hashlib.sha256(canonical_json_bytes(metadata)).hexdigest(),
                    nonce="0",
                    deadline=stamp + 3600,
                )
                proof = KeyProofMessage(
                    application_id=identifier_hash("D-app-" + template),
                    issuer_id=issuer,
                    signer=accounts[3],
                    challenge_nonce=identifier_hash("D-challenge-" + template),
                    deadline=stamp + 3600,
                )
                await send("propose", [proposal, proof, await sign(proof)], accounts[0])
                pid = proposal_id(domain, proposal)
                await send("approve", [pid], accounts[0])
                await send("approve", [pid], accounts[1])
                message = PublishMessage.model_validate(vector["typed_data"]["message"]).model_copy(
                    update={
                        "issuer_id": issuer,
                        "key_id": key,
                        "document_id": document_id(
                            issuer, vector["typed_data"]["message"]["docKey"]
                        ),
                        "issued_at": stamp - 300,
                        "expires_at": stamp + 7200,
                        "deadline": stamp + 3600,
                        "nonce": "0",
                        "version": 1,
                    }
                )
                content = dict(vector["protected_content"])
                if "due_at" in content:
                    content["due_at"] = stamp + 1800
                message = message.model_copy(
                    update={
                        "protected_hash": "0x"
                        + hashlib.sha256(canonical_json_bytes(content)).hexdigest()
                    }
                )
                raw = original_bytes(message, content)
                message = message.model_copy(
                    update={"original_hash": "0x" + hashlib.sha256(raw).hexdigest()}
                )
                signature = await sign(message)
                mined = await send("publish", [message, signature], accounts[4])
                material = VerificationMaterial(
                    signing_request=SigningRequest(
                        signing_request_id="wsr_D_live",
                        primary_type="Publish",
                        domain=domain,
                        message=message,
                        expected_signer=accounts[3],
                        content=content,
                        original_base64=base64.b64encode(raw).decode(),
                    ),
                    signature=signature,
                    block_number=str(int(mined["blockNumber"], 16)),
                    block_hash=mined["blockHash"],
                )
                directory = tmp_path / template
                directory.mkdir()
                paths = {
                    k: directory / k for k in ["material", "original", "candidate", "metadata"]
                }
                for k, value in {
                    "material": material.model_dump_json(),
                    "candidate": json.dumps(content),
                    "metadata": json.dumps(metadata),
                }.items():
                    paths[k].write_text(value)
                paths["original"].write_bytes(raw)
                args = SimpleNamespace(
                    material=str(paths["material"]),
                    original=str(paths["original"]),
                    candidate=None,
                    metadata=str(paths["metadata"]),
                    rpc_url=url,
                    chain_id="31337",
                    registry=address,
                )
                result = await support.module.verify(args)
                assert (
                    result.verification_status == "VERIFIED" and result.document.state == "ACTIVE"
                )
                assert result.comparison_scope == "FULL_COMPARISON"
                args.original, args.candidate = None, str(paths["candidate"])
                assert (await support.module.verify(args)).verification_status == "VERIFIED"
                changed = dict(content)
                field = "amount_minor" if "amount_minor" in changed else "title"
                changed[field] = (
                    changed[field] + 1 if field == "amount_minor" else "Changed synthetic title"
                )
                paths["candidate"].write_text(json.dumps(changed))
                assert (await support.module.verify(args)).verification_status == "TAMPERED"
                paths["candidate"].write_text(json.dumps(content))
                args.original, args.candidate = str(paths["original"]), None
                paths["original"].write_bytes(raw + b"altered")
                assert (await support.module.verify(args)).verification_status == "TAMPERED"
                paths["original"].write_bytes(raw)
                second = message.model_copy(update={"version": 2, "nonce": "1"})
                second = second.model_copy(
                    update={
                        "original_hash": "0x"
                        + hashlib.sha256(original_bytes(second, content)).hexdigest()
                    }
                )
                await send("publish", [second, await sign(second)], accounts[4])
                historic = await support.module.verify(args)
                assert (
                    historic.verification_status == "VERIFIED"
                    and historic.document.state == "SUPERSEDED"
                )
                revoke = RevokeMessage(
                    issuer_id=issuer,
                    doc_key=message.doc_key,
                    document_id=message.document_id,
                    version=2,
                    key_id=key,
                    nonce="2",
                    deadline=stamp + 3600,
                )
                await send("revoke", [revoke, await sign(revoke)], accounts[4])
                historic = await support.module.verify(args)
                assert (
                    historic.document.state == "SUPERSEDED"
                    and historic.document.latest_version == 2
                )
                report["scenarios"].append(
                    {
                        "template": template,
                        "original": "VERIFIED",
                        "protected_fields": "VERIFIED",
                        "original_tamper": "TAMPERED",
                        "field_tamper": "TAMPERED",
                        "superseded_after_latest_revoked": "PRESERVED",
                    }
                )
                last_args = args
            assert len(report["scenarios"]) == 2 and last_args is not None
            command("docker", "stop", name)
            assert (await support.module.verify(last_args)).verification_status == "INCONCLUSIVE"
            command("docker", "start", name)
            await ready()
            restored = await support.module.verify(last_args)
            assert (
                restored.verification_status == "VERIFIED"
                and restored.document.state == "SUPERSEDED"
            )
            report["rpc_stop_restart"] = "INCONCLUSIVE_THEN_VERIFIED_WITH_STATE_PRESERVED"
            report["status"] = "PASS"
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False, timeout=30)
        absent = subprocess.run(
            ["docker", "inspect", name], capture_output=True, check=False, timeout=30
        )
        report["resources_closed"] = absent.returncode != 0
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("x") as stream:
            report_path.chmod(0o600)
            json.dump(report, stream, indent=2)
        assert report["resources_closed"], "owned local EVM container must be removed"
