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
from originproof_core.ports import DependencyUnavailableError

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
