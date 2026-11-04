"""Demo-only DB tamper replay: listed demo accounts only, one synthetic notice, caught on verify."""

from test_wallet_runtime import activated, confirmed_publication, draft, payment_content

pytest_plugins = ("test_wallet_runtime",)

TARGET = payment_content() | {"amount_minor": 430000, "payee_account_number": "001234500010"}


async def verify(wallet, doc):
    return (
        await wallet.client.post(
            "/v3/verifications",
            json={
                "request_id": "req_v_" + str(id(doc))[-6:],
                "document_id": doc.document_id,
                "scope": "PROTECTED_FIELDS",
                "candidate": {"amount_minor": 430000},
            },
        )
    ).json()


async def test_demo_db_tamper_only_for_demo_account_and_caught(wallet):
    await activated(wallet)
    doc, _ = await confirmed_publication(wallet, await draft(wallet, content=TARGET))
    # Off by default: even a signed-in account sees no such route
    assert (await wallet.client.post("/v3/demo/db-tamper")).status_code == 404
    wallet.app.state.wallet_runtime.settings = wallet.app.state.wallet_runtime.settings.model_copy(
        update={"demo_attack_usernames": ["r"]}
    )
    assert (
        await wallet.client.post("/v3/demo/db-tamper")
    ).status_code == 404  # issuer "i" is not listed
    wallet.who["name"] = "recipient"
    tampered = await wallet.client.post("/v3/demo/db-tamper")
    assert tampered.status_code == 200, tampered.text
    assert tampered.json() | {"document_id": None} == {
        "document_id": None,
        "version": 1,
        "amount_before": 430000,
        "amount_after": 4300000,
    }
    result = await verify(wallet, doc)
    assert result["verification_status"] == "TAMPERED"
    assert any(c["reason_code"] == "STORED_CONTENT_MISMATCH" for c in result["checks"])
    restored = await wallet.client.post("/v3/demo/db-restore")
    assert restored.json()["amount_after"] == 430000
    assert (await verify(wallet, doc))["verification_status"] != "TAMPERED"
