"""D V5-W2 failure matrix; C #62 eaa0d16 helpers, ASGI/SQLite/synthetic Registry only."""

import socket
import time

import pytest
from originproof_core.wallet_contract import ProposalView
from originproof_core.wallet_ports import WalletProposal, WalletTransaction
from test_wallet_runtime import APPROVERS, BLOCK, ISSUER_HASH, prepared_proposal

pytest_plugins = ("test_wallet_runtime",)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    def denied(*args, **kwargs):
        raise AssertionError("D W2 QA permits only ASGI and in-memory SQLite")

    monkeypatch.setattr(socket.socket, "connect", denied)


@pytest.mark.parametrize(
    "actor,status",
    [("issuer", 403), ("other", 404)],
    ids=["W2-SELF-APPROVAL", "W2-OTHER-INSTITUTION"],
)
async def test_internal_approval_rejects_ineligible_actor(wallet, actor, status):
    """V5-F01: refusal does not activate an institution or submit a transaction."""
    wallet.who["name"] = actor
    response = await wallet.client.post(
        "/v3/issuer-applications/app_test/internal-approvals",
        json={"decision": "APPROVE", "reason": "D synthetic unauthorized approval"},
    )
    assert response.status_code == status, response.text
    assert wallet.chain.issuers == {} and wallet.chain.sends == []


@pytest.mark.parametrize("failure", ["domain", "code"], ids=["W2-EMAIL-DOMAIN", "W2-EMAIL-CODE"])
async def test_email_failures_do_not_create_chain_authority(wallet, failure):
    """V5-F01: approved-looking email text alone grants no authority."""
    issued = await wallet.client.post(
        "/v3/issuer-applications/app_test/email-codes",
        json={
            "email": "staff@unlisted.example.invalid"
            if failure == "domain"
            else "staff@bank.example.invalid"
        },
    )
    if failure == "domain":
        assert issued.status_code == 422, issued.text
    else:
        assert issued.status_code == 201, issued.text
        inbox = await wallet.client.get("/v3/issuer-applications/app_test/demo-inbox")
        correct = inbox.json()["code"]
        wrong = correct[:-1] + str((int(correct[-1]) + 1) % 10)
        response = await wallet.client.post(
            "/v3/issuer-applications/app_test/email-verifications", json={"code": wrong}
        )
        assert response.status_code == 422, response.text
    assert wallet.chain.issuers == {} and wallet.chain.sends == []


@pytest.mark.parametrize(
    "failure,status,code",
    [
        ("deadline", 410, "PROPOSAL_EXPIRED"),
        ("nonce", 409, "PROPOSAL_STALE"),
        ("issuer", 422, "KEY_PROOF_MISMATCH"),
        ("metadata", 422, "METADATA_HASH_MISMATCH"),
    ],
    ids=["W2-EXPIRED", "W2-STALE-NONCE", "W2-ISSUER-REPLACED", "W2-METADATA-REPLACED"],
)
async def test_changed_governance_intent_is_rejected(wallet, failure, status, code):
    """V5-F01/02/05: signed identity/metadata and fresh nonce/deadline remain binding."""
    _, original = await prepared_proposal(wallet)
    patch = {
        "deadline": {"deadline": int(time.time()) - 1},
        "nonce": {"nonce": "1"},
        "issuer": {"issuerId": "0x" + "fe" * 32},
        "metadata": {"metadataHash": "0x" + "ed" * 32},
    }[failure]
    response = await wallet.client.post(
        "/v3/proposals",
        json={
            **original,
            "request_id": "req_d_mutated",
            "proposal": original["proposal"] | patch,
        },
    )
    assert response.status_code == status and response.json()["detail"] == code, response.text
    assert ISSUER_HASH not in wallet.chain.issuers and wallet.chain.sends == []


@pytest.mark.parametrize(
    "approvals,state,status",
    [
        (APPROVERS[:1], "PENDING", 200),
        (APPROVERS[:2], "EXECUTED", 200),
        ([APPROVERS[0], APPROVERS[0]], "EXECUTED", 503),
    ],
    ids=["W2-ONE-APPROVER", "W2-TWO-DISTINCT-CONTROL", "W2-DUPLICATE-APPROVER"],
)
async def test_consumed_chain_approvals_are_distinct(wallet, approvals, state, status):
    """V5-F02: synthetic chain snapshots test C's consumer fence, not Solidity execution."""
    proposal, _ = await prepared_proposal(wallet)
    pid = proposal["proposal_id"]
    view = ProposalView.model_validate(proposal).model_copy(
        update={"approvals": approvals, "status": state}
    )
    wallet.chain.proposals[pid] = WalletProposal(**BLOCK, proposal=view)
    response = await wallet.client.get(f"/v3/proposals/{pid}")
    assert response.status_code == status, response.text
    if status == 200:
        assert response.json()["status"] == state
        assert response.json()["approvals"] == approvals
    assert wallet.chain.issuers == {} and wallet.chain.sends == []


async def test_confirmed_approval_receipt_without_effect_remains_unknown(wallet):
    """V5-F02/12: confirmed transaction alone does not prove approval or activation."""
    proposal, _ = await prepared_proposal(wallet)
    pid, tx = proposal["proposal_id"], "0x" + "da" * 32
    pending = ProposalView.model_validate(proposal).model_copy(update={"status": "PENDING"})
    wallet.chain.proposals[pid] = WalletProposal(**BLOCK, proposal=pending)
    wallet.chain.transactions[tx] = WalletTransaction(
        **BLOCK,
        tx_hash=tx,
        sender=APPROVERS[0],
        action="Approve",
        status="CONFIRMED",
        arguments={"proposalId": pid},
    )
    response = await wallet.client.post(
        f"/v3/proposals/{pid}/approvals",
        json={
            "request_id": "req_d_receipt_no_effect",
            "tx_hash": tx,
        },
    )
    assert response.status_code == 202 and response.json()["status"] == "UNKNOWN", response.text
    assert wallet.chain.issuers == {} and wallet.chain.sends == []
