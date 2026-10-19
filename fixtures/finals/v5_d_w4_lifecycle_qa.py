"""D V5-W4 lifecycle failures; C #62 eaa0d16 synthetic chain, no atomicity/EVM claim."""

import socket

import pytest
from eth_keys import keys
from originproof_api import wallet_documents
from originproof_api.wallet_database import WalletDocumentRow
from originproof_core.wallet_ports import WalletKey
from originproof_core.wallet_signatures import identifier_hash
from sqlalchemy.orm import Session
from test_wallet_runtime import (
    BLOCK,
    ISSUER_HASH,
    activated,
    confirmed_publication,
    confirmed_revocation,
    draft,
    sign,
)

pytest_plugins = ("test_wallet_runtime",)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    def denied(*args, **kwargs):
        raise AssertionError("D W4 QA permits only ASGI and in-memory SQLite")

    monkeypatch.setattr(socket.socket, "connect", denied)


async def verify(w, signing, doc):
    response = await w.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_d_state",
            "document_id": doc.document_id,
            "version": doc.version,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_old_version_does_not_revive_after_latest_revocation(wallet):
    """V5-F08/11: same ID, explicit old version, preserved original, revoked latest."""
    await activated(wallet)
    first = await draft(wallet)
    old, _ = await confirmed_publication(wallet, first)
    second = await draft(wallet, request_id="req_d_second", version=2)
    latest, _ = await confirmed_publication(wallet, second, req="req_d_publish2", tx_byte="68")
    await confirmed_revocation(wallet, latest.document_id, 2)
    history = await verify(wallet, first, old)
    assert history["verification_status"] == "VERIFIED"
    assert history["document"]["state"] == "SUPERSEDED"
    assert history["document"]["latest_version"] == 2
    current = await wallet.client.get(f"/v3/documents/{latest.document_id}")
    assert current.json()["state"] == "REVOKED" and current.json()["version"] == 2
    with Session(wallet.engine) as db:
        assert db.query(WalletDocumentRow).count() == 2
    assert wallet.chain.sends == []


async def test_revoked_version_stays_revoked_after_new_publication(wallet):
    """V5-F08: synthetic Registry must preserve revocation and refuse another revoke."""
    await activated(wallet)
    first = await draft(wallet)
    old, _ = await confirmed_publication(wallet, first)
    await confirmed_revocation(wallet, old.document_id, 1)
    second = await draft(wallet, request_id="req_d_after_revoke", version=2)
    latest, _ = await confirmed_publication(wallet, second, req="req_d_successor", tx_byte="68")
    history = await verify(wallet, first, old)
    assert history["verification_status"] == "VERIFIED"
    assert history["document"]["state"] == "REVOKED"
    assert history["document"]["latest_version"] == 2
    current = await wallet.client.get(f"/v3/documents/{latest.document_id}")
    assert current.json()["state"] == "ACTIVE" and current.json()["version"] == 2
    nonce = wallet.chain.issuers[ISSUER_HASH].next_nonce
    denied = await wallet.client.post(
        "/v3/revoke-drafts",
        json={"request_id": "req_d_revoke_again", "document_id": old.document_id, "version": 1},
    )
    assert denied.status_code == 409 and denied.json()["detail"] == "DOCUMENT_ALREADY_REVOKED"
    assert wallet.chain.issuers[ISSUER_HASH].next_nonce == nonce and wallet.chain.sends == []


async def test_competing_draft_reservation_is_not_two_successful_publications(wallet):
    """V5-F08: sequential API reservation fence only; actual concurrent chain test is pending."""
    await activated(wallet)
    first = await draft(wallet)
    second = await draft(wallet, request_id="req_d_competing")
    responses = []
    for i, value in enumerate((first, second)):
        responses.append(
            await wallet.client.post(
                "/v3/publications",
                json={
                    "request_id": f"req_d_compete_{i}",
                    "signing_request_id": value["signing_request_id"],
                    "signature": sign(value),
                },
            )
        )
    assert [r.status_code for r in responses] == [202, 409]
    assert responses[0].json()["status"] != "CONFIRMED"
    assert wallet.chain.documents == {} and wallet.chain.sends == []


async def test_suspended_institution_can_revoke_but_cannot_publish(wallet):
    """V5-F03/09: current-key revocation stays possible during an emergency suspension."""
    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    waiting = await draft(wallet, request_id="req_d_waiting", version=2)
    wallet.chain.issuers[ISSUER_HASH] = wallet.chain.issuers[ISSUER_HASH].model_copy(
        update={"state": "SUSPENDED"}
    )
    blocked = await wallet.client.post(
        "/v3/publications",
        json={
            "request_id": "req_d_blocked",
            "signing_request_id": waiting["signing_request_id"],
            "signature": sign(waiting),
        },
    )
    assert blocked.status_code == 409 and blocked.json()["detail"] == "ISSUER_SUSPENDED"
    await confirmed_revocation(wallet, doc.document_id, 1)
    result = await verify(wallet, signing, doc)
    assert result["verification_status"] == "VERIFIED"
    assert result["document"]["state"] == "REVOKED"
    assert "ISSUER_SUSPENDED" in result["document"]["warnings"]


async def test_key_rotation_preserves_history_and_rejects_old_signer(wallet):
    """V5-F05/09: old valid signature and permission to issue now are independent."""
    await activated(wallet)
    signing = await draft(wallet)
    doc, _ = await confirmed_publication(wallet, signing)
    new_id = identifier_hash("d_rotated_key")
    signer = keys.PrivateKey((5).to_bytes(32, "big")).public_key.to_checksum_address().lower()
    wallet.chain.keys[doc.key_id] = wallet.chain.keys[doc.key_id].model_copy(
        update={"retired_block": "11"}
    )
    wallet.chain.keys[new_id] = WalletKey(
        **(BLOCK | {"block_number": "12"}),
        key_id=new_id,
        issuer_id=ISSUER_HASH,
        signer=signer,
        registered_block="11",
    )
    wallet.chain.issuers[ISSUER_HASH] = wallet.chain.issuers[ISSUER_HASH].model_copy(
        update={"key_id": new_id, "signer": signer}
    )
    for records in (wallet.chain.issuers, wallet.chain.keys, wallet.chain.documents):
        for identity, value in list(records.items()):
            records[identity] = value.model_copy(update={"block_number": "12"})
    past = await verify(wallet, signing, doc)
    assert past["verification_status"] == "VERIFIED"
    future = await draft(wallet, request_id="req_d_new_key", version=2)
    sends_before = list(wallet.chain.sends)
    denied = await wallet.client.post(
        "/v3/publications",
        json={
            "request_id": "req_d_old_signer",
            "signing_request_id": future["signing_request_id"],
            "signature": sign(future),
        },
    )
    assert denied.status_code == 422, denied.text
    assert denied.json()["detail"] == "INVALID_SIGNATURE"
    assert wallet.chain.sends == sends_before
    wallet.chain.keys[doc.key_id] = wallet.chain.keys[doc.key_id].model_copy(
        update={"compromise_block": "12"}
    )
    warning = await verify(wallet, signing, doc)
    assert warning["verification_status"] == "VERIFIED"
    assert "KEY_COMPROMISED" in warning["document"]["warnings"]


async def test_expired_signature_is_rejected_without_sending(wallet, monkeypatch):
    """V5-F05: trusted API test clock at exact deadline, no OS-clock mutation."""
    await activated(wallet)
    signing = await draft(wallet)
    monkeypatch.setattr(wallet_documents, "now", lambda: signing["message"]["deadline"])
    response = await wallet.client.post(
        "/v3/publications",
        json={
            "request_id": "req_d_expired",
            "signing_request_id": signing["signing_request_id"],
            "signature": sign(signing),
        },
    )
    assert response.status_code == 410 and response.json()["detail"] == "SIGNATURE_EXPIRED"
    assert wallet.chain.documents == {} and wallet.chain.sends == []
