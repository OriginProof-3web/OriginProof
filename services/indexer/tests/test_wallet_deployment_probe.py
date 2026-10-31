"""Offline guard checks for the read-only Sepolia deployment evidence command."""

import json
from types import SimpleNamespace

import httpx
import pytest
import verify_wallet_deployment as probe


@pytest.mark.parametrize(
    "fault", [None, "genesis", "approvers", "write", "provider", "http_429", "http_502"]
)
async def test_probe_reports_failures_without_writes_or_rpc_credentials(
    tmp_path, monkeypatch, capsys, fault
):
    approvers = ["0x" + digit * 40 for digit in "123"]
    contract = {"address": approvers[0], "constructor_arguments": [approvers]}
    manifest = {
        "contracts": {"OriginProofWalletRegistry": contract},
        "creation_bytecode": "0x60", "genesis_block_hash": "0xgenesis",
        "deployment_block": 1, "deployment_block_hash": "0xblock",
        "runtime_code_hash": "0xruntime",
    }
    contracts = tmp_path / "packages/contracts"
    (contracts / "deployments").mkdir(parents=True)
    (contracts / "deployments/11155111.wallet.json").write_text(json.dumps(manifest))
    artifact = contracts / "out/OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({"bytecode": {"object": "0x60"}}))
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    monkeypatch.setenv("SEPOLIA_RPC_URL", "https://rpc.invalid/SECRET")
    monkeypatch.setattr(probe.subprocess, "check_output", lambda *a, **kw: "a" * 40)
    monkeypatch.setattr(probe, "load_wallet_deployment", lambda *a, **kw: (
        {}, SimpleNamespace(tx_hash="0xtx", creation_bytecode=b"\x60")
    ))

    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda req: httpx.Response(
        429 if fault == "http_429" else 502, text="<html>SECRET provider error</html>"
    ))
    monkeypatch.setattr(probe.httpx, "AsyncClient", lambda **kw: original_client(
        transport=transport, **kw
    ))

    class Rpc:
        def __init__(self, client, url, **kw):
            self.client, self.url = client, url

        async def block(self, tag):
            return {"hash": "bad" if fault == "genesis" else "0xgenesis"}

        async def snapshot(self):
            return {"number": "0x2", "hash": "0xhead"}

    async def approver_check(rpc, proof):
        if fault == "write":
            await rpc.client.post(rpc.url, json={"method": "eth_sendRawTransaction"})
        if fault == "provider":
            raise ValueError("https://rpc.invalid/SECRET")
        if fault in {"http_429", "http_502"}:
            await rpc.client.post(rpc.url, json={"method": "eth_getCode"})
        return [] if fault == "approvers" else approvers

    monkeypatch.setattr(probe, "WalletRpc", Rpc)
    monkeypatch.setattr(probe, "verified_approvers", approver_check)
    assert await probe.verify() is (fault is None)
    output = capsys.readouterr().out
    assert "SECRET" not in output
    report = json.loads(output)
    assert report["writes"] == 0
    assert len(report["attempts"]) == (3 if fault is None else 1)
    assert report["attempts"][0]["status"] == ("PASS" if fault is None else "FAIL")
    if fault in {"http_429", "http_502"}:
        assert report["attempts"][0]["rpc_calls"] == [{
            "method": "eth_getCode", "http_status": int(fault[5:]), "rpc_error_code": None,
        }]
