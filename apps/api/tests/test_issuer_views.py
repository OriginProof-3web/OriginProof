"""v5 issuer screens: my chain state and key, my published notices; issuers only."""

from test_wallet_runtime import activated, confirmed_publication, draft

pytest_plugins = ("test_wallet_runtime",)


async def test_issuer_state_and_documents(wallet):
    await activated(wallet)
    state = await wallet.client.get("/v3/issuer/state")
    assert state.status_code == 200, state.text
    assert (state.json()["state"], state.json()["key_status"]) == ("ACTIVE", "ACTIVE")
    first = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, first)
    second = await draft(wallet, request_id="req_second", version=2)
    await confirmed_publication(wallet, second, req="req_publish2", tx_byte="68")
    listed = (await wallet.client.get("/v3/issuer/documents")).json()["documents"]
    assert [(d["version"], d["latest_version"]) for d in listed] == [(2, 2), (1, 2)]
    assert listed[0]["document_id"] == doc.document_id and listed[0]["amount_minor"] == 154000
    wallet.who["name"] = "recipient"
    assert (await wallet.client.get("/v3/issuer/state")).status_code == 403
    assert (await wallet.client.get("/v3/issuer/documents")).status_code == 403
