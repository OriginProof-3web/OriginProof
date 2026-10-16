"""D V5-W3 content/DB failure matrix; immutable C #62 eaa0d16, no real chain/browser."""

import socket

import pytest
from originproof_api.database import AccountRow, IssuerApplicationRow
from originproof_api.wallet_database import WalletDocumentRow, WalletOnboardingRow
from sqlalchemy.orm import Session
from test_wallet_runtime import DOMAIN, activated, confirmed_publication, draft

pytest_plugins = ("test_wallet_runtime",)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    def denied(*args, **kwargs):
        raise AssertionError("D W3 QA permits only ASGI and in-memory SQLite")

    monkeypatch.setattr(socket.socket, "connect", denied)


async def publication(w, template="payment"):
    if template == "official":
        office = "iss_origin_mock_office"
        for name in ("issuer", "internal"):
            w.accounts[name].issuer_id = office
        w.app.state.settings.wallet_internal_approvers = {office: "acct_internal"}
        with Session(w.engine) as db:
            for aid in ("acct_i", "acct_internal"):
                db.get(AccountRow, aid).issuer_id = office
            application = db.get(IssuerApplicationRow, "app_test")
            application.issuer_id, application.issuer_name = office, "Origin Mock Office"
            db.commit()
        await activated(w, issuer_id=office, domain="office")
    else:
        await activated(w)
    content = (
        None
        if template == "payment"
        else {
            "notice_type": "OFFICIAL_DOCUMENT",
            "institution_code": "ORIGIN_MOCK_OFFICE",
            "document_type": "합성 공고",
            "document_number": "D-QA-1",
            "title": "합성 일정 안내",
            "summary": "공식 창구에서 일정을 확인하세요",
            "official_url": "https://office.example.invalid",
        }
    )
    signing = await draft(w, content=content)
    doc, _ = await confirmed_publication(w, signing)
    return signing, doc


async def verify(w, signing, doc, **patch):
    response = await w.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_d_compare",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
            **patch,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "template,field,value",
    [
        ("payment", "amount_minor", 154001),
        ("payment", "payee_account_number", "999999990001"),
        ("payment", "official_url", "https://changed.example.invalid/pay"),
        ("official", "title", "변경된 합성 일정"),
        ("official", "official_url", "https://changed.example.invalid/notice"),
    ],
    ids=["W3-AMOUNT", "W3-ACCOUNT", "W3-PAYMENT-URL", "W3-TITLE", "W3-OFFICIAL-URL"],
)
async def test_single_field_tampering_preserves_original(wallet, template, field, value):
    """V5-F07: change only one field in a full candidate; compare original afterward."""
    signing, doc = await publication(wallet, template)
    changed = signing["content"] | {field: value}
    assert sum(changed[k] != signing["content"][k] for k in changed) == 1
    result = await verify(wallet, signing, doc, candidate=changed)
    assert result["verification_status"] == "TAMPERED"
    assert "PROTECTED_FIELDS_MISMATCH" in result["reason_codes"]
    original = await verify(wallet, signing, doc)
    assert original["verification_status"] == "VERIFIED"
    assert wallet.chain.sends == []


@pytest.mark.parametrize("scope", ["ID_ONLY", "PARTIAL"], ids=["W3-ID-ONLY", "W3-PARTIAL"])
async def test_copied_id_or_partial_candidate_does_not_prove_complete_content(wallet, scope):
    """V5-F07/11: a copied document ID cannot authenticate an attached message."""
    signing, doc = await publication(wallet)
    patch = (
        {"scope": "ID_ONLY", "candidate": None}
        if scope == "ID_ONLY"
        else {
            "candidate": {"amount_minor": signing["content"]["amount_minor"]},
        }
    )
    result = await verify(wallet, signing, doc, **patch)
    assert result["verification_status"] == "INCONCLUSIVE"
    assert result["comparison_scope"] == ("ID_ONLY" if scope == "ID_ONLY" else "PARTIAL_COMPARISON")
    assert wallet.chain.sends == []


@pytest.mark.parametrize(
    "change",
    ["original", "content", "metadata", "name", "message"],
    ids=["W3-DB-BYTES", "W3-DB-CONTENT", "W3-DB-METADATA", "W3-DB-NAME", "W3-DB-VERSION"],
)
async def test_database_tampering_is_not_treated_as_authority(wallet, change):
    """V5-F10: DB tampering must fail against unchanged signed/Registry commitments."""
    signing, doc = await publication(wallet)
    before = dict(wallet.chain.documents)
    with Session(wallet.engine) as db:
        row = db.get(WalletDocumentRow, ("31337", DOMAIN.verifying_contract, doc.document_id, 1))
        if change == "original":
            row.original += b"\n"
        elif change == "content":
            row.content = row.content | {"amount_minor": 154001}
        elif change == "metadata":
            onboarding = db.get(WalletOnboardingRow, "app_test")
            onboarding.metadata_value = onboarding.metadata_value | {
                "domain": "changed.example.invalid"
            }
        elif change == "name":
            db.get(IssuerApplicationRow, "app_test").issuer_name = "Changed Synthetic Institution"
        else:
            row.message = row.message | {"version": 2}
        db.commit()
    result = await verify(wallet, signing, doc)
    assert result["verification_status"] == "TAMPERED", result
    assert wallet.chain.documents == before and wallet.chain.sends == []


async def test_missing_original_is_unavailable_rather_than_tampered(wallet):
    """V5-F10: deletion is a lack of comparison evidence, not evidence of forgery."""
    signing, doc = await publication(wallet)
    with Session(wallet.engine) as db:
        row = db.get(WalletDocumentRow, ("31337", DOMAIN.verifying_contract, doc.document_id, 1))
        row.original = None
        db.commit()
    result = await verify(wallet, signing, doc)
    assert result["verification_status"] == "INCONCLUSIVE"
    assert "ORIGINAL_UNAVAILABLE" in result["reason_codes"]
