"""Governance request identity and proposal preconditions before proof consumption."""

import time

import pytest
from originproof_api.database import IssuerApplicationRow, OperationRow
from originproof_api.operations import input_fingerprint
from originproof_api.wallet_database import WalletSigningRow
from originproof_core.wallet_ports import WalletIssuer, WalletKey
from originproof_core.wallet_signatures import identifier_hash
from sqlalchemy.orm import Session
from test_wallet_runtime import (
    APPROVERS,
    BLOCK,
    ISSUER,
    ISSUER_HASH,
    SIGNER,
    onboarding,
    proved_key,
    sign,
)

pytest_plugins = ("test_wallet_runtime",)


async def test_key_proof_request_id_conflicts_across_challenges(wallet):
    _, first, body = await proved_key(wallet)
    retry = await wallet.client.post("/v3/key-proofs", json=body)
    assert retry.status_code == 200
    second = await wallet.client.post(
        "/v3/key-challenges",
        json={"request_id": "req_second", "application_id": "app_test", "signer": SIGNER},
    )
    signing = second.json()
    changed = body | {
        "signing_request_id": signing["signing_request_id"],
        "signature": sign(signing),
    }
    conflict = await wallet.client.post("/v3/key-proofs", json=changed)
    assert conflict.status_code == 409 and conflict.json()["detail"] == "REQUEST_ID_CONFLICT"
    with Session(wallet.engine) as db:
        assert db.get(WalletSigningRow, signing["signing_request_id"]).verified_at is None
    accepted = await wallet.client.post(
        "/v3/key-proofs", json=changed | {"request_id": "req_second_proof"}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["signing_request_id"] != first["signing_request_id"]


@pytest.mark.parametrize("case", ["zero_key", "same_signer", "new_signer"])
async def test_proposal_preconditions_are_checked_before_consuming_key_proof(wallet, case):
    checks, signing, _ = await proved_key(wallet)
    key_id = "0x" + "00" * 32 if case == "zero_key" else identifier_hash("new_key")
    if case != "zero_key":
        old_key = identifier_hash("old_key")
        old_signer = SIGNER if case == "same_signer" else APPROVERS[0]
        wallet.chain.issuers[ISSUER_HASH] = WalletIssuer(
            **BLOCK,
            issuer_id=ISSUER_HASH,
            state="ACTIVE",
            key_id=old_key,
            signer=old_signer,
            metadata_hash=checks["metadata_hash"],
            next_nonce="0",
            governance_nonce="0",
        )
        wallet.chain.keys[old_key] = WalletKey(
            **BLOCK,
            key_id=old_key,
            issuer_id=ISSUER_HASH,
            signer=old_signer,
            registered_block="1",
        )
    wallet.who["name"] = "operator"
    body = {
        "request_id": "req_proposal_guard",
        "key_proof_request_id": signing["signing_request_id"],
        "proposal": {
            "action": 1 if case == "zero_key" else 2,
            "issuerId": ISSUER_HASH,
            "keyId": key_id,
            "signer": SIGNER,
            "metadataHash": checks["metadata_hash"],
            "nonce": "0",
            "deadline": signing["message"]["deadline"],
        },
    }
    response = await wallet.client.post("/v3/proposals", json=body)
    assert response.status_code == {"zero_key": 422, "same_signer": 409, "new_signer": 201}[case]
    with Session(wallet.engine) as db:
        consumed = db.get(WalletSigningRow, signing["signing_request_id"]).consumed_by
    if case == "new_signer":
        assert consumed == response.json()["proposal_id"]
    else:
        assert consumed is None
        assert response.json()["detail"] == (
            "INVALID_KEY_ID" if case == "zero_key" else "SIGNER_ALREADY_USED"
        )
    if case == "zero_key":
        body["proposal"]["keyId"] = identifier_hash("valid_key")
        accepted = await wallet.client.post("/v3/proposals", json=body)
        assert accepted.status_code == 201, accepted.text


@pytest.mark.parametrize("action", ["wallet_propose", "wallet_approve", "wallet_suspend"])
async def test_governance_transaction_retries_expire(wallet, action):
    target, tx_hash = ISSUER_HASH, "0x" + "ab" * 32
    body = {"request_id": "req_old_governance", "tx_hash": tx_hash}
    fingerprint = input_fingerprint(
        body if action == "wallet_suspend" else body | {"proposal_id": target}
    )
    with Session(wallet.engine) as db:
        db.add(
            OperationRow(
                operation_id="op_old_governance",
                account_id="acct_o",
                action=action,
                request_id=body["request_id"],
                input_hash=fingerprint,
                status="CONFIRMED",
                recovery_reference={"resolved_at": int(time.time()) - 30 * 86400},
                target_id=target,
            )
        )
        db.commit()
    wallet.who["name"] = "operator"
    if action == "wallet_suspend":
        path = f"/v3/issuers/{target}/suspensions"
    else:
        path = f"/v3/proposals/{target}/" + (
            "approvals" if action == "wallet_approve" else "transactions"
        )
    response = await wallet.client.post(path, json=body)
    assert response.status_code == 410, response.text


async def test_rejected_application_cannot_continue_to_key_proof(wallet):
    await onboarding(wallet)
    with Session(wallet.engine) as db:
        db.get(IssuerApplicationRow, "app_test").status = "REJECTED"
        db.commit()
    response = await wallet.client.post(
        "/v3/key-challenges",
        json={"request_id": "req_rejected", "application_id": "app_test", "signer": SIGNER},
    )
    assert response.status_code == 409 and response.json()["detail"] == "APPLICATION_REJECTED"


async def test_reissued_email_code_keeps_internal_rejection(wallet):
    c = wallet.client
    await c.post(
        "/v3/issuer-applications/app_test/email-codes", json={"email": "staff@bank.example.invalid"}
    )
    code = (await c.get("/v3/issuer-applications/app_test/demo-inbox")).json()["code"]
    await c.post("/v3/issuer-applications/app_test/email-verifications", json={"code": code})
    wallet.who["name"] = "internal"
    rejected = await c.post(
        "/v3/issuer-applications/app_test/internal-approvals",
        json={"decision": "REJECT", "reason": "not our staff"},
    )
    assert rejected.status_code == 200, rejected.text
    wallet.who["name"] = "issuer"
    reissue = await c.post(
        "/v3/issuer-applications/app_test/email-codes", json={"email": "staff@bank.example.invalid"}
    )
    assert reissue.status_code == 409
    assert reissue.json()["detail"] == "INTERNAL_APPROVAL_REJECTED"


async def test_suspension_accepts_roster_slug_and_pending_tx_is_retryable(wallet):
    wallet.who["name"] = "operator"
    body = {"request_id": "req_suspend", "tx_hash": "0x" + "cd" * 32}
    for _ in range(2):  # same answer on retry while the transaction is not visible
        pending = await wallet.client.post(f"/v3/issuers/{ISSUER}/suspensions", json=body)
        assert pending.status_code == 503, pending.text
        assert pending.json()["detail"] == "TRANSACTION_PENDING"
    bad = await wallet.client.post("/v3/issuers/not-a-slug/suspensions", json=body)
    assert bad.status_code == 422
