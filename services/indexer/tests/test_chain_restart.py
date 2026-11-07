"""Opt-in W6 local chain restart with disposable Anvil instances."""

import asyncio
import json
import os
import shutil
import socket
import subprocess

import httpx
import pytest
from deploy_local import deploy
from eth_keys import keys
from infrastructure.blockchain.reader import JsonRpcBlockchainReader
from infrastructure.blockchain.writer import ChainOperationState, JsonRpcBlockchainWriter
from originproof_core.ports import DependencyUnavailableError
from originproof_indexer import ProjectionStore, decode_proof_log
from originproof_indexer.projection import PROOF_CONSUMED, PROOF_REGISTERED, PROOF_REVOKED
from sqlalchemy import create_engine

pytestmark = pytest.mark.skipif(os.environ.get("W6_LIVE_TEST") != "1", reason="local EVM opt-in")


async def test_same_chain_id_redeployment_invalidates_old_manifest(tmp_path):
    anvil = shutil.which("anvil")
    assert anvil, "anvil is required"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    signer = keys.PrivateKey(os.urandom(32)).public_key.to_checksum_address()
    process = None

    async def rpc(method, params):
        async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
            response = await client.post(
                url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            )
            response.raise_for_status()
            body = response.json()
            assert "error" not in body
            return body["result"]

    async def start():
        nonlocal process
        process = subprocess.Popen(
            [anvil, "--chain-id", "31337", "--port", str(port), "--silent"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                if await rpc("eth_chainId", []) == "0x7a69":
                    return
            except httpx.TransportError:
                await asyncio.sleep(0.05)
        pytest.fail("disposable Anvil did not start")

    def stop():
        nonlocal process
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        process = None

    try:
        await start()
        first_path = await asyncio.to_thread(deploy, url, signer, "0" * 40)
        first = json.loads(first_path.read_text())
        old_path = tmp_path / "old-manifest.json"
        old_path.write_text(json.dumps(first))
        assert (await rpc("eth_chainId", [])) == "0x7a69"
        writer = JsonRpcBlockchainWriter(url, old_path, receipt_attempts=1, poll_interval=0)
        prepared = await writer.prepare_suspend_issuer(
            first["roles"]["issuer_manager"], "iss_origin_mock_bank"
        )
        await rpc("anvil_setAutomine", [False])
        submitted = await writer.submit_prepared(prepared)
        assert submitted.state == ChainOperationState.SUBMITTED
        pending = await writer.confirm_prepared(prepared, submitted.tx_hash)
        assert pending.state == ChainOperationState.UNKNOWN
        assert pending.error_code == "RECEIPT_UNKNOWN"
        await rpc("evm_mine", [])
        await rpc("anvil_setAutomine", [True])
        confirmed = await writer.recover_prepared(prepared, submitted.tx_hash)
        assert confirmed.state == ChainOperationState.CONFIRMED
        assert confirmed.tx_hash == submitted.tx_hash

        projection_engine = create_engine("sqlite:///" + str(tmp_path / "reorg.db"))
        try:
            projection = ProjectionStore(projection_engine)
            projection.initialize()
            snapshot = await rpc("evm_snapshot", [])
            base_tip = int(await rpc("eth_blockNumber", []), 16)
            for _ in range(3):
                await rpc("evm_mine", [])

            def scan():
                with httpx.Client(timeout=2, trust_env=False) as client:

                    def sync_rpc(method, params):
                        response = client.post(
                            url,
                            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                        )
                        response.raise_for_status()
                        body = response.json()
                        assert "error" not in body
                        return body["result"]

                    def block_hash_at(number):
                        block = sync_rpc("eth_getBlockByNumber", [hex(number), False])
                        return block["hash"]

                    def logs_at(number):
                        raw = sync_rpc(
                            "eth_getLogs",
                            [
                                {
                                    "address": first["contracts"]["ProofStatusRegistry"]["address"],
                                    "fromBlock": hex(number),
                                    "toBlock": hex(number),
                                    "topics": [[PROOF_REGISTERED, PROOF_CONSUMED, PROOF_REVOKED]],
                                }
                            ],
                        )
                        return [decode_proof_log(log, 31337, first["deployment_id"]) for log in raw]

                    return projection.sync_confirmed(
                        31337,
                        first["deployment_id"],
                        first["deployment_block"],
                        lambda: int(sync_rpc("eth_blockNumber", []), 16),
                        block_hash_at,
                        logs_at,
                    )

            old_checkpoint = await asyncio.to_thread(scan)
            assert old_checkpoint[0] == base_tip + 2
            assert await rpc("evm_revert", [snapshot])
            accounts = await rpc("eth_accounts", [])
            await rpc(
                "eth_sendTransaction",
                [{"from": accounts[0], "to": accounts[1], "value": "0x0"}],
            )
            await rpc("evm_mine", [])
            await rpc("evm_mine", [])
            while int(await rpc("eth_blockNumber", []), 16) < old_checkpoint[0] + 1:
                await rpc("evm_mine", [])
            new_checkpoint = await asyncio.to_thread(scan)
            assert new_checkpoint[0] == old_checkpoint[0]
            assert new_checkpoint[1] != old_checkpoint[1]
        finally:
            projection_engine.dispose()
        stop()

        await start()
        accounts = await rpc("eth_accounts", [])
        await rpc(
            "eth_sendTransaction",
            [{"from": accounts[0], "to": accounts[1], "value": "0x0"}],
        )
        second_path = await asyncio.to_thread(deploy, url, signer, "0" * 40)
        second = json.loads(second_path.read_text())
        assert second["chain_id"] == first["chain_id"] == 31337
        assert second["deployment_id"] != first["deployment_id"]
        assert second["deployment_block"] > first["deployment_block"]
        assert (
            second["contracts"]["IssuerRegistry"]["address"]
            != first["contracts"]["IssuerRegistry"]["address"]
        )
        old_address = first["contracts"]["IssuerRegistry"]["address"]
        new_address = second["contracts"]["IssuerRegistry"]["address"]
        assert await rpc("eth_getCode", [old_address, "latest"]) == "0x"
        assert await rpc("eth_getCode", [new_address, "latest"]) != "0x"
        assert (
            await rpc(
                "eth_getLogs",
                [
                    {
                        "address": old_address,
                        "fromBlock": hex(second["deployment_block"]),
                        "toBlock": "latest",
                    }
                ],
            )
            == []
        )
        assert second["roles"]["issuer_account"] == first["roles"]["issuer_account"]
        old_reader = JsonRpcBlockchainReader(url, old_path, issuer_ids=["iss_origin_mock_bank"])
        with pytest.raises(DependencyUnavailableError):
            await old_reader.get_issuer("iss_origin_mock_bank")
        new_reader = JsonRpcBlockchainReader(url, second_path, issuer_ids=["iss_origin_mock_bank"])
        key = await new_reader.get_key("key_origin_mock_bank_001")
        assert key.signer.lower() == signer.lower()
    finally:
        stop()
