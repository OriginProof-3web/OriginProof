"""Track B (#88): lookup of a published record from a message without a document ID."""

import time

from originproof_api.wallet_database import WalletVerificationRow
from originproof_core.wallet_signatures import identifier_hash
from sqlalchemy.orm import Session
from test_wallet_runtime import activated, confirmed_publication, draft, payment_content

pytest_plugins = ("test_wallet_runtime",)

KEY = {
    "notice_type": "PAYMENT_REQUEST",
    "amount_minor": 154000,
    "currency": "KRW",
    "payee_account_number": "001-234-567890",  # as printed in a message
}


async def lookup(wallet, issuer_id, key=KEY, request_id="req_lookup"):
    return await wallet.client.post(
        "/v3/document-lookups",
        json={"request_id": request_id, "issuer_id": issuer_id, "key": key},
    )


async def test_lookup_unverified_then_matched_with_partial_verification(wallet):
    await activated(wallet)
    signing = await draft(wallet)
    issuer = signing["message"]["issuerId"]
    before = await lookup(wallet, issuer)
    assert before.status_code == 200, before.text
    assert before.json() == {
        "lookup_status": "UNVERIFIED",
        "match_count": 0,
        "document_ids": [],
        "verification": None,
        "reason_codes": ["NO_MATCHING_RETAINED_RECORD"],
    }
    doc, _ = await confirmed_publication(wallet, signing)
    matched = (await lookup(wallet, issuer)).json()
    assert (matched["lookup_status"], matched["document_ids"]) == ("MATCHED", [doc.document_id])
    verification = matched["verification"]
    # A few matching fields never become VERIFIED; chain state is still checked.
    assert verification["comparison_scope"] == "PARTIAL_COMPARISON"
    assert verification["verification_status"] == "INCONCLUSIVE"
    assert verification["document"]["state"] == "ACTIVE"
    with Session(wallet.engine) as db:
        assert db.get(WalletVerificationRow, verification["session_id"]) is not None
    for issuer_id, key in (
        (issuer, KEY | {"amount_minor": 154001}),
        (identifier_hash("iss_other_bank"), KEY),
    ):
        missed = (await lookup(wallet, issuer_id, key)).json()
        assert missed["lookup_status"] == "UNVERIFIED" and missed["verification"] is None


async def test_lookup_prefers_latest_matching_version(wallet):
    await activated(wallet)
    first = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, first)
    second = await draft(wallet, request_id="req_second", version=2)
    await confirmed_publication(wallet, second, req="req_publish2", tx_byte="68")
    matched = (await lookup(wallet, first["message"]["issuerId"])).json()
    assert matched["lookup_status"] == "MATCHED" and matched["match_count"] == 1
    assert matched["verification"]["document"]["version"] == 2
    assert matched["reason_codes"] == ["OLDER_VERSIONS_ALSO_MATCH"]


async def test_lookup_reports_ambiguity_instead_of_choosing(wallet):
    await activated(wallet)
    first = await draft(wallet)
    doc1, _ = await confirmed_publication(wallet, first)
    response = await wallet.client.post(
        "/v3/document-drafts",
        json={
            "request_id": "req_other_notice",
            "doc_key": identifier_hash("other_notice"),
            "expected_version": 1,
            "expires_at": int(time.time()) + 86400,
            "content": payment_content(),
        },
    )
    assert response.status_code == 201, response.text
    doc2, _ = await confirmed_publication(
        wallet, response.json(), req="req_publish_other", tx_byte="69"
    )
    result = (await lookup(wallet, first["message"]["issuerId"])).json()
    assert result["lookup_status"] == "AMBIGUOUS" and result["match_count"] == 2
    assert result["document_ids"] == sorted([doc1.document_id, doc2.document_id])
    assert result["verification"] is None


async def test_lookup_rejects_malformed_key(wallet):
    response = await lookup(
        wallet, identifier_hash("iss_origin_mock_bank"), KEY | {"payee_account_number": "abc"}
    )
    assert response.status_code == 422
