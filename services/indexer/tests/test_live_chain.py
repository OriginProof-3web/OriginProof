"""Opt-in local EVM + real M1 API test. No private key is persisted or printed."""

import asyncio
import json
import os
import shutil
import socket
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from deploy_local import deploy
from eth_keys import keys
from infrastructure.blockchain.reader import JsonRpcBlockchainReader
from infrastructure.blockchain.reader import digest as chain_digest
from infrastructure.blockchain.writer import ChainOperationState, JsonRpcBlockchainWriter
from originproof_api.main import create_app
from originproof_core import (
    CardPaymentNoticeCandidate,
    SignedProofEnvelope,
    VerificationService,
    signing_digest,
)
from originproof_indexer import ProjectionStore, decode_proof_log
from originproof_indexer.projection import PROOF_CONSUMED, PROOF_REGISTERED, PROOF_REVOKED
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(os.environ.get("M4_LIVE_TEST") != "1", reason="local EVM opt-in")


async def test_live_reader_and_m1_api():
    rpc_url = os.environ.get("M4_RPC_URL")
    process = None
    if rpc_url is None:
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
            source_sha = os.environ.get("M4_SOURCE_COMMIT_SHA", "0" * 40)
            manifest_path = await asyncio.to_thread(
                deploy, rpc_url, public_signer, source_commit_sha=source_sha
            )
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
            snapshot = await reader.get_issuer_key_snapshot(
                envelope.issuer_id, envelope.key_id, envelope.issued_at
            )
            assert snapshot.issuer == issuer
            assert snapshot.key == key
            assert snapshot.key_valid_at
            assert snapshot.deployment_id == manifest["deployment_id"]
            assert snapshot.chain_id == manifest["chain_id"]
            assert snapshot.block_number >= manifest["deployment_block"]
            assert snapshot.block_hash.startswith("0x") and len(snapshot.block_hash) == 66
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

                writer = JsonRpcBlockchainWriter(rpc_url, manifest_path, client=rpc_client)
                latest_block = await rpc("eth_getBlockByNumber", ["latest", False])
                now = int(latest_block["timestamp"], 16)
                proof_id = "prf_w4_live_synthetic"
                subject = "0x" + chain_digest("synthetic subject").hex()
                register = await writer.prepare_register_proof(
                    manifest["roles"]["gateway"],
                    proof_id,
                    envelope.issuer_id,
                    envelope.key_id,
                    golden["signing_digest"],
                    subject,
                    int(key.valid_from.timestamp()),
                    now + 1000,
                    True,
                )
                submitted = await writer.submit_prepared(register)
                assert submitted.state == ChainOperationState.SUBMITTED
                confirmed = await writer.confirm_prepared(register, submitted.tx_hash)
                assert confirmed.state == ChainOperationState.CONFIRMED
                state = await reader.get_proof_state(proof_id, datetime.fromtimestamp(now, UTC))
                assert state.status == "ACTIVE" and state.consumable_at
                assert state.signing_digest == golden["signing_digest"]
                consume = await writer.prepare_consume_proof(
                    manifest["roles"]["gateway"], proof_id, 1, subject
                )
                submitted = await writer.submit_prepared(consume)
                assert submitted.state == ChainOperationState.SUBMITTED
                assert (await writer.confirm_prepared(consume, submitted.tx_hash)).state == (
                    ChainOperationState.CONFIRMED
                )
                state = await reader.get_proof_state(proof_id, datetime.fromtimestamp(now, UTC))
                assert state.status == "CONSUMED" and not state.consumable_at
                replay = await writer.prepare_consume_proof(
                    manifest["roles"]["gateway"], proof_id, 1, subject
                )
                replay_submitted = await writer.submit_prepared(replay)
                assert replay_submitted.state == ChainOperationState.SUBMITTED
                assert (await writer.confirm_prepared(replay, replay_submitted.tx_hash)).state == (
                    ChainOperationState.FAILED
                )
                revoke = await writer.prepare_revoke_proof(
                    manifest["roles"]["issuer_account"], proof_id
                )
                submitted = await writer.submit_prepared(revoke)
                assert submitted.state == ChainOperationState.SUBMITTED
                assert (await writer.confirm_prepared(revoke, submitted.tx_hash)).state == (
                    ChainOperationState.CONFIRMED
                )
                state = await reader.get_proof_state(proof_id, datetime.fromtimestamp(now, UTC))
                assert state.status == "REVOKED" and state.consumed_at is not None
                raw_logs = await rpc(
                    "eth_getLogs",
                    [
                        {
                            "address": manifest["contracts"]["ProofStatusRegistry"]["address"],
                            "fromBlock": hex(manifest["deployment_block"]),
                            "toBlock": "latest",
                            "topics": [[PROOF_REGISTERED, PROOF_CONSUMED, PROOF_REVOKED]],
                        }
                    ],
                )
                projection_engine = create_engine("sqlite://")
                try:
                    projection = ProjectionStore(projection_engine)
                    projection.initialize()
                    proof_logs = [
                        decode_proof_log(raw, 31337, manifest["deployment_id"]) for raw in raw_logs
                    ]
                    assert [log.event_type for log in proof_logs] == [
                        "REGISTERED",
                        "CONSUMED",
                        "REVOKED",
                    ]
                    tip = int(await rpc("eth_blockNumber", []), 16)
                    for number in range(manifest["deployment_block"], tip + 1):
                        block = await rpc("eth_getBlockByNumber", [hex(number), False])
                        logs = [log for log in proof_logs if log.event.block_number == number]
                        assert projection.apply_block(
                            31337, manifest["deployment_id"], number, block["hash"], logs
                        )
                        assert not projection.apply_block(
                            31337, manifest["deployment_id"], number, block["hash"], logs
                        )
                    assert projection.verified_checkpoint(
                        31337,
                        manifest["deployment_id"],
                        lambda number: block["hash"] if number == tip else None,
                    ) == (tip, block["hash"])
                    proof_hash = "0x" + chain_digest(proof_id).hex()
                    assert (
                        projection.projected_proof_status(
                            31337, manifest["deployment_id"], proof_hash
                        )
                        == "REVOKED"
                    )
                finally:
                    projection_engine.dispose()
                rejected = await writer.suspend_issuer(
                    manifest["roles"]["registry_admin"], envelope.issuer_id
                )
                assert rejected.state == ChainOperationState.FAILED
                assert rejected.error_code == "CHAIN_REVERTED"

                suspended = await writer.suspend_issuer(
                    manifest["roles"]["issuer_manager"], envelope.issuer_id
                )
                assert suspended.state == ChainOperationState.CONFIRMED
                assert not await reader.is_key_valid(envelope.key_id, key.valid_from)
                assert (await verify(request))["lifecycle_status"] == "ISSUER_SUSPENDED"
                reactivated = await writer.reactivate_issuer(
                    manifest["roles"]["issuer_manager"], envelope.issuer_id
                )
                assert reactivated.state == ChainOperationState.CONFIRMED
                revoked = await writer.revoke_key(
                    manifest["roles"]["issuer_account"], envelope.key_id
                )
                assert revoked.state == ChainOperationState.CONFIRMED
                assert (await reader.get_key(envelope.key_id)).status == "REVOKED"
                assert not await reader.is_key_valid(envelope.key_id, key.valid_from)
                assert (await verify(request))["lifecycle_status"] == "ISSUER_KEY_REVOKED"
                if process is not None:
                    process.terminate()
                    await asyncio.to_thread(process.wait, 5)
                    unavailable = await verify(request)
                    assert unavailable["verification_status"] == "INCONCLUSIVE"
                    assert unavailable["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
            await app.state.database.dispose()
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
