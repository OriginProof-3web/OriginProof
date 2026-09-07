"""Opt-in local EVM + real M1 API test. No private key is persisted or printed."""

import asyncio
import json
import os
import shutil
import socket
import subprocess
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from deploy_local import deploy
from eth_keys import keys
from infrastructure.blockchain.reader import JsonRpcBlockchainReader, digest
from originproof_api.main import create_app
from originproof_core import (
    CardPaymentNoticeCandidate,
    SignedProofEnvelope,
    VerificationService,
    signing_digest,
)

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(os.environ.get("M4_LIVE_TEST") != "1", reason="local EVM opt-in")


async def test_live_reader_and_m1_api():
    anvil = shutil.which("anvil")
    assert anvil, "anvil is required for the opt-in test"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    rpc_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [anvil, "--chain-id", "31337", "--port", str(port), "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        async with httpx.AsyncClient(timeout=2, trust_env=False) as rpc_client:

            async def rpc(method, params):
                response = await rpc_client.post(
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
                assert "error" not in body
                return body["result"]

            for _ in range(100):
                try:
                    await rpc("eth_chainId", [])
                    break
                except httpx.TransportError:
                    await asyncio.sleep(0.05)
            else:
                pytest.fail("local anvil did not start")

            private_key = keys.PrivateKey(os.urandom(32))
            public_signer = private_key.public_key.to_checksum_address()
            manifest_path = await asyncio.to_thread(deploy, rpc_url, public_signer)
            manifest = json.loads(manifest_path.read_text())
            golden = json.loads(
                (ROOT / "fixtures/golden/card_payment_notice_signing_v1.json").read_text()
            )
            envelope = SignedProofEnvelope.model_validate(
                golden["signing_payload"]
                | {"payload": golden["payload"], "signature": "0x" + "00" * 65}
            )
            assert signing_digest(envelope) == golden["signing_digest"]
            signature = private_key.sign_msg_hash(bytes.fromhex(golden["signing_digest"][2:]))
            envelope = envelope.model_copy(update={"signature": "0x" + signature.to_bytes().hex()})
            reader = JsonRpcBlockchainReader(
                rpc_url, manifest_path, issuer_ids=[envelope.issuer_id]
            )
            issuer = await reader.get_issuer(envelope.issuer_id)
            key = await reader.get_key(envelope.key_id)
            assert issuer.status == "ACTIVE" and key.status == "ACTIVE"
            assert key.issuer_id == envelope.issuer_id
            assert key.signer.lower() == public_signer.lower()
            assert key.valid_from == envelope.issued_at
            assert await reader.is_key_valid(envelope.key_id, key.valid_from)
            assert not await reader.is_key_valid(
                envelope.key_id, key.valid_from - timedelta(seconds=1)
            )
            assert not await reader.is_key_valid(envelope.key_id, key.valid_until)
            assert await reader.get_issuer("iss_missing") is None
            assert await reader.get_key("key_missing") is None

            class Proofs:
                async def get_proof(self, proof_id):
                    return envelope if proof_id == envelope.proof_id else None

            app = create_app(VerificationService(Proofs(), reader))
            candidate = CardPaymentNoticeCandidate(**golden["payload"], confidence=1)
            request = {
                "proof_id": envelope.proof_id,
                "request_id": "req_live_chain",
                "candidate": candidate.model_dump(mode="json"),
            }
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://test"
            ) as api:

                async def verify(body):
                    response = await api.post("/v1/mvp/card-notices/verify", json=body)
                    assert response.status_code == 200
                    return response.json()

                normal = await verify(request)
                assert normal["verification_status"] == "VERIFIED"
                assert normal["lifecycle_status"] == "ACTIVE"
                changed = request | {"candidate": request["candidate"] | {"amount_minor": 1540000}}
                tampered = await verify(changed)
                assert tampered["verification_status"] == "TAMPERED"
                assert "AMOUNT_MISMATCH" in tampered["reason_codes"]

                admin = (await rpc("eth_accounts", []))[0]

                async def send(contract, function, identifier):
                    tx = await rpc(
                        "eth_sendTransaction",
                        [
                            {
                                "from": admin,
                                "to": manifest["contracts"][contract]["address"],
                                "gas": "0x50000",
                                "data": "0x" + (digest(function)[:4] + digest(identifier)).hex(),
                            }
                        ],
                    )
                    for _ in range(100):
                        receipt = await rpc("eth_getTransactionReceipt", [tx])
                        if receipt:
                            assert int(receipt["status"], 16) == 1
                            return
                        await asyncio.sleep(0.05)
                    pytest.fail("transaction not mined")

                await send("IssuerRegistry", "suspendIssuer(bytes32)", envelope.issuer_id)
                assert not await reader.is_key_valid(envelope.key_id, key.valid_from)
                assert (await verify(request))["lifecycle_status"] == "ISSUER_SUSPENDED"
                await send("IssuerRegistry", "reactivateIssuer(bytes32)", envelope.issuer_id)
                await send("IssuerKeyRegistry", "revokeKey(bytes32)", envelope.key_id)
                assert (await reader.get_key(envelope.key_id)).status == "REVOKED"
                assert not await reader.is_key_valid(envelope.key_id, key.valid_from)
                assert (await verify(request))["lifecycle_status"] == "ISSUER_KEY_REVOKED"
                process.terminate()
                await asyncio.to_thread(process.wait, 5)
                unavailable = await verify(request)
                assert unavailable["verification_status"] == "INCONCLUSIVE"
                assert unavailable["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
            await app.state.database.dispose()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
