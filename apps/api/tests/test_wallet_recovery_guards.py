"""HTTP regressions for request claims, chain preconditions and durable recovery."""

import time
from datetime import UTC, datetime, timedelta

import pytest
from originproof_api.database import AuditEventRow, OperationRow
from originproof_api.wallet_database import WalletRequestRow
from originproof_core import DependencyUnavailableError
from originproof_core.wallet_contract import SigningRequest
from originproof_core.wallet_ports import WalletTransaction
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_wallet_runtime import (
    APPROVERS,
    BLOCK,
    ISSUER,
    activated,
    confirmed_publication,
    draft,
    sign,
)

pytest_plugins = ("test_wallet_runtime",)


async def publish(w, signing, request_id):
    return await w.client.post(
        "/v3/publications",
        json={
            "request_id": request_id,
            "signing_request_id": signing["signing_request_id"],
            "signature": sign(signing),
        },
    )


@pytest.mark.parametrize("change", ["address", "chain_id"])
async def test_pending_nonce_reservation_is_scoped_to_its_deployment(wallet, change):
    await activated(wallet)
    old = await draft(wallet, request_id="req_old_draft")
    accepted = await publish(wallet, old, "req_old_publish")
    assert accepted.status_code == 202, accepted.text
    same = await publish(wallet, await draft(wallet, request_id="req_same_draft"), "req_same")
    assert same.status_code == 409 and same.json()["detail"] == "NONCE_ALREADY_RESERVED"
    settings = wallet.app.state.settings
    if change == "address":
        settings.wallet_registry_address = "0x" + "34" * 20
    else:
        settings.blockchain_chain_id = 31338
    domain = wallet.app.state.wallet_runtime.domain
    for rows in (wallet.chain.issuers, wallet.chain.keys):
        for key, value in rows.items():
            rows[key] = value.model_copy(
                update={
                    "chain_id": domain.chain_id,
                    "verifying_contract": domain.verifying_contract,
                }
            )
    new = await draft(wallet, request_id="req_new_draft")
    assert new["domain"] != old["domain"] and new["message"]["nonce"] == old["message"]["nonce"]
    submitted = await publish(wallet, new, "req_new_publish")
    assert submitted.status_code == 202, submitted.text
    repeat = await publish(wallet, await draft(wallet, request_id="req_repeat"), "req_repeat")
    assert repeat.status_code == 409 and repeat.json()["detail"] == "NONCE_ALREADY_RESERVED"
    stale = await wallet.client.post(f"/v3/operations/{accepted.json()['operation_id']}/reconcile")
    assert stale.status_code == 409 and stale.json()["detail"] == "DEPLOYMENT_CHANGED"
    with Session(wallet.engine) as db:
        row = db.get(OperationRow, accepted.json()["operation_id"])
        assert row.status == accepted.json()["status"] and row.error_code is None
        assert row.recovery_reference["domain"] == old["domain"]
    assert wallet.chain.sends == []


async def test_reconcile_keeps_bound_hash_over_a_stale_lookup_candidate(wallet):
    await activated(wallet)
    signing = await draft(wallet)
    accepted = await publish(wallet, signing, "req_publish")
    operation_id = accepted.json()["operation_id"]
    bound, stale = "0x" + "91" * 32, "0x" + "92" * 32
    message = SigningRequest.model_validate(signing).message
    wallet.chain.transactions[bound] = WalletTransaction(
        **BLOCK,
        tx_hash=bound,
        sender=APPROVERS[0],
        action="Publish",
        status="SUBMITTED",
        arguments={"message": message.model_dump(by_alias=True), "signature": sign(signing)},
    )

    async def direct(request_id, tx_hash):
        return await wallet.client.post(
            f"/v3/signing-requests/{signing['signing_request_id']}/transactions",
            json={
                "request_id": request_id,
                "signing_request_id": signing["signing_request_id"],
                "tx_hash": tx_hash,
            },
        )

    first = await direct("req_bound", bound)
    assert first.status_code == 202 and first.json()["status"] == "SUBMITTED", first.text
    # PostgreSQL race: the losing intake saved its lookup intent before A was bound.
    with Session(wallet.engine) as db:
        row = db.get(OperationRow, operation_id)
        row.recovery_reference = row.recovery_reference | {"lookup_tx_hash": stale}
        db.commit()
    rejected = await direct("req_stale", stale)
    assert rejected.status_code == 409 and rejected.json()["detail"] == "DIRECT_TX_ALREADY_BOUND"
    reconciled = await wallet.client.post(f"/v3/operations/{operation_id}/reconcile")
    assert reconciled.status_code == 202, reconciled.text
    assert reconciled.json()["status"] == "SUBMITTED" and reconciled.json()["tx_hash"] == bound
    assert wallet.chain.sends == []


@pytest.mark.parametrize("bad_candidate", [False, True])
async def test_reconcile_uses_saved_hash_and_searches_past_an_invalid_candidate(
    wallet, bad_candidate
):
    await activated(wallet)
    signing = await draft(wallet)
    _, result = await confirmed_publication(wallet, signing)
    operation_id, tx_hash = result["operation_id"], result["tx_hash"]
    with Session(wallet.engine) as db:
        row = db.get(OperationRow, operation_id)
        row.status, row.tx_hash = "UNKNOWN", None
        row.recovery_reference = {"domain": row.recovery_reference["domain"]}
        db.commit()
    transaction = wallet.chain.transaction
    lookup = "0x" + "99" * 32 if bad_candidate else tx_hash
    if bad_candidate:
        wallet.chain.transactions[lookup] = wallet.chain.transactions[tx_hash].model_copy(
            update={"tx_hash": lookup, "arguments": {}}
        )

    async def unavailable(_):
        raise DependencyUnavailableError("synthetic interrupted lookup")

    wallet.chain.transaction = unavailable
    response = await wallet.client.post(
        f"/v3/signing-requests/{signing['signing_request_id']}/transactions",
        json={
            "request_id": "req_interrupted",
            "signing_request_id": signing["signing_request_id"],
            "tx_hash": lookup,
        },
    )
    assert response.status_code == 503, response.text
    looked_up = []

    async def restored(value):
        looked_up.append(value)
        return await transaction(value)

    async def search(intent):
        if not bad_candidate:
            raise AssertionError("known valid hash must recover without intent search")
        assert looked_up == [lookup]
        return wallet.chain.transactions[tx_hash]

    wallet.chain.transaction, wallet.chain.find_transaction = restored, search
    recovered = await wallet.client.post(f"/v3/operations/{operation_id}/reconcile")
    assert recovered.status_code == 202, recovered.text
    assert recovered.json()["status"] == "CONFIRMED"
    assert recovered.json()["tx_hash"] == tx_hash
    assert looked_up == ([lookup, tx_hash] if bad_candidate else [tx_hash])
    assert wallet.chain.sends == []


@pytest.mark.parametrize("state", ["PENDING_SUBMISSION", "SUBMITTED", "UNKNOWN", "FAILED"])
async def test_legacy_and_v3_views_agree_on_wallet_recovery(wallet, state):
    await activated(wallet)
    signing = await draft(wallet)
    _, result = await confirmed_publication(wallet, signing)
    with Session(wallet.engine) as db:
        row = db.get(OperationRow, result["operation_id"])
        row.status = state
        row.error_code = "SIGNATURE_EXPIRED" if state == "FAILED" else None
        db.commit()
    path = f"/operations/{result['operation_id']}"
    legacy = (await wallet.client.get("/v1" + path)).json()
    current = (await wallet.client.get("/v3" + path)).json()
    listed = (await wallet.client.get("/v1/operations")).json()
    assert listed[0]["next_action"] == legacy["next_action"] == current["next_action"]
    assert legacy["recovery_required"] == current["recovery_required"]
    assert legacy["next_action"] == ("RESIGN" if state == "FAILED" else "RECONCILE")


@pytest.mark.parametrize(
    "endpoint", ["get", "submission", "alias", "direct", "reconcile", "legacy_get", "legacy_list"]
)
async def test_operation_expiry_is_enforced_before_cleanup(wallet, monkeypatch, endpoint):
    await activated(wallet)
    signing = await draft(wallet)
    _, operation = await confirmed_publication(wallet, signing)
    with Session(wallet.engine) as db:
        resolved = db.get(OperationRow, operation["operation_id"]).recovery_reference["resolved_at"]
    future = resolved + 30 * 86400
    monkeypatch.setattr(time, "time", lambda: future)
    if endpoint in ("get", "legacy_get"):
        version = "v1" if endpoint == "legacy_get" else "v3"
        response = await wallet.client.get(f"/{version}/operations/{operation['operation_id']}")
    elif endpoint == "legacy_list":
        response = await wallet.client.get("/v1/operations")
        assert response.status_code == 200 and response.json() == []
        return
    elif endpoint == "reconcile":
        response = await wallet.client.post(f"/v3/operations/{operation['operation_id']}/reconcile")
    elif endpoint in ("submission", "alias"):
        response = await wallet.client.post(
            "/v3/publications",
            json={
                "request_id": "req_publish" if endpoint == "submission" else "req_expired_alias",
                "signing_request_id": signing["signing_request_id"],
                "signature": sign(signing),
            },
        )
    else:
        response = await wallet.client.post(
            f"/v3/signing-requests/{signing['signing_request_id']}/transactions",
            json={
                "request_id": "req_expired_direct",
                "signing_request_id": signing["signing_request_id"],
                "tx_hash": operation["tx_hash"],
            },
        )
    assert response.status_code == 410, response.text
    assert response.json()["detail"] == "RESULT_EXPIRED"
    with Session(wallet.engine) as db:
        assert (
            db.scalar(
                select(WalletRequestRow).where(
                    WalletRequestRow.request_id.in_(("req_expired_alias", "req_expired_direct"))
                )
            )
            is None
        )


@pytest.mark.parametrize("offset", [-1, 0, 1])
async def test_operation_access_at_the_retention_boundary(wallet, monkeypatch, offset):
    await activated(wallet)
    signing = await draft(wallet)
    _, operation = await confirmed_publication(wallet, signing)
    with Session(wallet.engine) as db:
        resolved = db.get(OperationRow, operation["operation_id"]).recovery_reference["resolved_at"]
    monkeypatch.setattr(time, "time", lambda: resolved + 30 * 86400 + offset)
    for prefix in ("/v1", "/v3"):
        response = await wallet.client.get(prefix + "/operations/" + operation["operation_id"])
        assert response.status_code == (200 if offset < 0 else 410), response.text
    listed = await wallet.client.get("/v1/operations")
    assert len(listed.json()) == (1 if offset < 0 else 0)


@pytest.mark.parametrize("offset", [-1, 0, 1])
async def test_unprotected_audit_access_at_the_retention_boundary(wallet, monkeypatch, offset):
    stamp = int(time.time())
    with Session(wallet.engine) as db:
        db.add(
            AuditEventRow(
                event_id="evt_boundary",
                actor_account_id="acct_i",
                issuer_id=ISSUER,
                action="wallet_analysis",
                target_id="ana_boundary",
                after_status="FAILED",
                created_at=datetime.fromtimestamp(stamp - 30 * 86400, UTC),
            )
        )
        db.commit()
    monkeypatch.setattr(time, "time", lambda: stamp + offset)
    response = await wallet.client.get("/v1/audit-events")
    assert response.status_code == 200, response.text
    assert len(response.json()) == (1 if offset < 0 else 0)


async def test_retention_filters_precede_pagination_and_keep_unresolved_audits(wallet):
    stamp = int(time.time())
    old = datetime.fromtimestamp(stamp, UTC) - timedelta(days=31)
    cases = [
        ("a_expired", "wallet_publish", "CONFIRMED", stamp - 30 * 86400, False),
        ("b_failed", "wallet_publish", "FAILED", stamp - 30 * 86400, False),
        ("c_unknown", "wallet_publish", "UNKNOWN", 1, True),
        ("d_unstamped", "wallet_publish", "CONFIRMED", None, True),
        ("e_legacy", "publish", "CONFIRMED", 1, True),
        ("f_lookalike", "walletXpublish", "CONFIRMED", 1, True),
        ("g_recent", "wallet_publish", "CONFIRMED", stamp - 86400, True),
    ]
    with Session(wallet.engine) as db:
        for name, action, status, resolved, _ in cases:
            db.add(
                OperationRow(
                    operation_id="op_" + name,
                    account_id="acct_i",
                    issuer_id=ISSUER,
                    action=action,
                    request_id="req_" + name,
                    input_hash="0" * 64,
                    status=status,
                    recovery_reference={
                        "resolved_at": resolved,
                        "domain": wallet.app.state.wallet_runtime.domain.model_dump(by_alias=True),
                    },
                    target_id=name,
                    created_at=old,
                )
            )
            db.add(
                AuditEventRow(
                    event_id="evt_" + name,
                    actor_account_id="acct_i",
                    issuer_id=ISSUER,
                    action=action,
                    target_id=name,
                    after_status=status,
                    created_at=old,
                )
            )
        db.commit()
    expected = ["op_" + c[0] for c in cases if c[-1]]
    all_operations = await wallet.client.get("/v1/operations")
    assert [row["operation_id"] for row in all_operations.json()] == expected
    all_audits = await wallet.client.get("/v1/audit-events")
    assert [row["event_id"] for row in all_audits.json()] == [
        value.replace("op_", "evt_", 1) for value in expected
    ]
    for name in ("c_unknown", "d_unstamped", "g_recent"):
        response = await wallet.client.get("/v3/operations/op_" + name)
        assert response.status_code == 200, response.text
    listed = await wallet.client.get("/v1/operations?limit=1")
    assert [row["operation_id"] for row in listed.json()] == expected[:1]
    audits = await wallet.client.get("/v1/audit-events?limit=1")
    assert [row["event_id"] for row in audits.json()] == [expected[0].replace("op_", "evt_", 1)]
    wallet.who["name"] = "other"
    for prefix in ("/v1", "/v3"):
        response = await wallet.client.get(prefix + "/operations/op_a_expired")
        assert response.status_code == 404, response.text
