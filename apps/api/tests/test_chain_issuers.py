"""Public list of synthetic institutions that are ACTIVE on the registry (state from chain only)."""

from originproof_core.wallet_ports import WalletIssuer
from originproof_core.wallet_signatures import identifier_hash
from test_wallet_runtime import BLOCK, SIGNER

pytest_plugins = ("test_wallet_runtime",)


def issuer(name, state):
    hashed = identifier_hash(name)
    return hashed, WalletIssuer(
        **BLOCK,
        issuer_id=hashed,
        state=state,
        key_id=identifier_hash("key_" + name),
        signer=SIGNER,
        metadata_hash="0x" + "11" * 32,
        next_nonce="0",
        governance_nonce="0",
    )


async def test_only_chain_active_roster_issuers_are_listed(wallet):
    empty = await wallet.client.get("/v1/chain/issuers")
    assert empty.status_code == 200 and empty.json() == {"issuers": []}
    cases = (("iss_origin_mock_bank", "ACTIVE"), ("iss_origin_mock_office", "SUSPENDED"))
    for name, state in cases:
        hashed, row = issuer(name, state)
        wallet.chain.issuers[hashed] = row
    body = (await wallet.client.get("/v1/chain/issuers")).json()
    assert body == {
        "issuers": [
            {"name": "Origin Mock Bank", "issuer_id": identifier_hash("iss_origin_mock_bank")}
        ]
    }


async def test_network_view_includes_public_registry_address(wallet):
    body = (await wallet.client.get("/v1/chain/network")).json()
    assert body["registry_address"] == wallet.app.state.settings.wallet_registry_address
