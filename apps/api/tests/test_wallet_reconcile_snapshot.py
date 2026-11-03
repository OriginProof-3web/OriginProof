"""Pinned recovery reads use the production adapter (synthetic RPC, no network)."""

import pytest
from infrastructure.blockchain.errors import BlockchainDependencyError
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from originproof_core import DependencyUnavailableError


@pytest.mark.parametrize("changed", [False, True])
async def test_recovery_adapter_pins_absent_issuer_and_document(changed):
    block = {"number": "0xa", "hash": "0x" + "ab" * 32, "timestamp": "0x123"}
    calls = []

    class Rpc:
        async def snapshot(self):
            calls.append("snapshot")
            return block

        async def call(self, name, arguments, pinned):
            assert pinned is block
            calls.append(name)
            return (0,) if name == "latestVersion" else None

        async def check(self, pinned):
            assert pinned is block
            calls.append("check")
            if changed:
                raise BlockchainDependencyError("synthetic reorg")

    adapter = WalletRegistryReadAdapter(Rpc())
    pinned = await adapter.snapshot()
    for read in (
        adapter.issuer("0x" + "12" * 32, pinned),
        adapter.document("0x" + "34" * 32, 1, pinned),
    ):
        if changed:
            with pytest.raises(DependencyUnavailableError):
                await read
        else:
            assert await read is None
    assert calls == ["snapshot", "getIssuer", "check", "latestVersion", "getDocument", "check"]
