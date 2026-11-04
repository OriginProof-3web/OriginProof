"""v5 issuer screens: my chain state and key, my published notices, registration trail."""

from originproof_core.wallet_contract import ProposalView
from originproof_core.wallet_ports import WalletProposal
from test_wallet_runtime import (
    APPROVERS,
    BLOCK,
    activated,
    confirmed_publication,
    draft,
    prepared_proposal,
)

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


async def test_registration_trail_names_each_step_and_scopes_by_role(wallet):
    data, _ = await prepared_proposal(wallet)
    executed = ProposalView.model_validate(data).model_copy(
        update={"status": "EXECUTED", "approvals": APPROVERS[:2]}
    )
    wallet.chain.proposals[data["proposal_id"]] = WalletProposal(**BLOCK, proposal=executed)
    for who in ("operator", "issuer", "internal"):
        wallet.who["name"] = who
        response = await wallet.client.get("/v3/issuer/registrations")
        assert response.status_code == 200, response.text
        (trail,) = response.json()["trails"]
        assert (trail["applicant"], trail["internal_approver"]) == ("i", "in")
        assert trail["email_verified"] and trail["internally_approved"]
        (step,) = trail["proposals"]
        assert (step["proposer"], step["status"], step["approvers"]) == (
            "o",
            "EXECUTED",
            ["o", "o2"],
        )
    wallet.who["name"] = "other"
    assert (await wallet.client.get("/v3/issuer/registrations")).json()["trails"] == []
    wallet.who["name"] = "recipient"
    assert (await wallet.client.get("/v3/issuer/registrations")).status_code == 403
