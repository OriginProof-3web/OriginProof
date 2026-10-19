"""HTTP + durable DB failure/permission checks; synthetic chain, separate live EVM gate."""

import asyncio
from dataclasses import replace

import test_finals_proofs as w3
from infrastructure.blockchain.writer import ChainOperationState
from originproof_api.database import FinalsProofRow, OperationRow, RecipientTokenRow
from sqlalchemy import delete
from sqlalchemy.orm import Session

context = w3.context
finals = w3.finals


async def test_consume_competition_permissions_replay_and_revoke(finals):
    client, manager, selected, accounts, recipients, _ = finals
    proof = (await client.post("/v2/issuer/proofs", json=w3.body())).json()
    assert proof["registration_status"] == "CONFIRMED"
    identifier = proof["proof_id"]
    path = f"/v2/proofs/{identifier}/consume"
    selected[0] = accounts[0]
    assert (await client.post(path, json={"request_id": "req_admin"})).status_code == 404
    selected[0] = accounts[2]
    assert (await client.post(path, json={"request_id": "req_other"})).status_code == 404
    selected[0] = recipients[1]
    assert (await client.post(path, json={"request_id": "req_other_recipient"})).status_code == 404
    selected[0] = recipients[0]
    assert (
        await client.post(path, json={"request_id": "req_csrf"}, headers={"X-CSRF-Token": "wrong"})
    ).status_code == 403
    assert (
        await client.post(path, json={"request_id": "req_override", "actor_kind": 0})
    ).status_code == 422
    assert (
        await client.post(
            f"/v2/issuer/proofs/{identifier}/revoke",
            json={"request_id": "req_not_owner", "reason": "test"},
        )
    ).status_code == 403
    first, second = await asyncio.gather(
        *[client.post(path, json={"request_id": f"req_compete_{i}"}) for i in range(2)]
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    winner = first if first.status_code == 200 else second
    again = await client.post(path, json={"request_id": winner.json()["request_id"]})
    assert again.json()["operation_id"] == winner.json()["operation_id"]
    assert (await client.post(path, json={"request_id": "req_replay"})).json()[
        "detail"
    ] == "REPLAY_DETECTED"
    assert len([s for s in manager.writer.submissions if s.action == "consume_proof"]) == 1
    verified = await client.post(
        f"/v2/proofs/{identifier}/verify", json={"request_id": "req_verify"}
    )
    assert verified.json()["lifecycle_status"] == "CONSUMED"
    selected[0] = accounts[1]
    revoke = f"/v2/issuer/proofs/{identifier}/revoke"
    revoked = await client.post(revoke, json={"request_id": "req_revoke", "reason": "test"})
    assert revoked.json()["status"] == "CONFIRMED"
    assert (
        await client.post(revoke, json={"request_id": "req_revoke", "reason": "changed"})
    ).status_code == 409
    unchanged = await client.post(revoke, json={"request_id": "req_revoke_again", "reason": "test"})
    assert unchanged.json()["chain_evidence"]["no_change"]
    assert unchanged.json()["tx_hash"] is None
    assert len([s for s in manager.writer.submissions if s.action == "revoke_proof"]) == 1
    state = manager.proof_states[identifier]
    assert state.consumed_at is not None
    verified = await client.post(
        f"/v2/proofs/{identifier}/verify", json={"request_id": "req_revoked"}
    )
    assert verified.json()["verification_status"] == "VERIFIED"
    assert verified.json()["lifecycle_status"] == "PROOF_REVOKED"
    assert set(verified.json()["reason_codes"]) == {"PROOF_REVOKED", "REPLAY_DETECTED"}


async def test_old_registration_missing_mismatch_expiry_and_binding(finals):
    client, manager, selected, accounts, recipients, engine = finals
    original = (await client.post("/v2/issuer/proofs", json=w3.body())).json()
    identifier = original["proof_id"]
    with Session(engine) as db:
        row = db.get(FinalsProofRow, identifier)
        signed = row.envelope.copy()
        db.execute(delete(OperationRow).where(OperationRow.action == "register_proof"))
        db.commit()
    saved_state = manager.proof_states.pop(identifier)
    result = await client.post(
        f"/v2/proofs/{identifier}/verify", json={"request_id": "req_missing"}
    )
    assert result.json()["verification_status"] == "NOT_REGISTERED"
    assert result.json()["lifecycle_status"] is None
    registration = await client.post(
        f"/v2/issuer/proofs/{identifier}/register", json={"request_id": "req_backfill"}
    )
    assert registration.json()["status"] == "CONFIRMED"
    with Session(engine) as db:
        assert db.get(FinalsProofRow, identifier).envelope == signed
    manager.proof_states[identifier] = replace(saved_state, signing_digest="0x" + "ff" * 32)
    result = await client.post(
        f"/v2/proofs/{identifier}/verify", json={"request_id": "req_mismatch"}
    )
    assert result.json()["reason_codes"] == ["CHAIN_COMMITMENT_MISMATCH"]
    assert result.json()["lifecycle_status"] is None
    manager.proof_states[identifier] = saved_state
    selected[0] = accounts[2]
    document = (await client.post("/v2/issuer/proofs", json=w3.body("OFFICIAL_DOCUMENT"))).json()
    assert (
        await client.post(
            f"/v2/proofs/{document['proof_id']}/consume", json={"request_id": "req_document"}
        )
    ).json()["detail"] == "PROOF_NOT_SINGLE_USE"
    selected[0] = accounts[1]
    assert (
        await client.post(
            f"/v2/proofs/{document['proof_id']}/consume", json={"request_id": "req_backfill"}
        )
    ).status_code == 404
    # Even the authenticated issuing institution cannot use a lost recipient binding.
    with Session(engine) as db:
        db.get(RecipientTokenRow, recipients[0].account_id).token = "ff" * 32
        db.commit()
    assert (
        await client.post(
            f"/v2/proofs/{identifier}/consume", json={"request_id": "req_lost_binding"}
        )
    ).json()["detail"] == "SUBJECT_BINDING_MISMATCH"
    # A schema-invalid persisted envelope fails without any external consume.
    with Session(engine) as db:
        row = db.get(FinalsProofRow, identifier)
        original_envelope = row.envelope
        row.envelope = original_envelope | {"proof_id": "prf_different"}
        db.commit()
    assert (
        await client.post(
            f"/v2/proofs/{identifier}/consume",
            json={
                "request_id": "req_bad_identity",
            },
        )
    ).json()["detail"] == "INVALID_STORED_PROOF"
    with Session(engine) as db:
        db.get(FinalsProofRow, identifier).envelope = original_envelope
        db.commit()
    manager.rpc_failure = True
    assert (
        await client.post(f"/v2/proofs/{identifier}/consume", json={"request_id": "req_rpc"})
    ).status_code == 503


async def test_unknown_registration_consume_recovery_and_failed_receipt(finals):
    client, manager, _, _, _, engine = finals
    manager.writer.state = ChainOperationState.UNKNOWN
    request = w3.body()
    created = await client.post("/v2/issuer/proofs", json=request)
    identifier = created.json()["proof_id"]
    assert created.json()["registration_status"] == "UNKNOWN"
    assert (
        await client.post(f"/v2/proofs/{identifier}/verify", json={"request_id": "req_pending"})
    ).json()["verification_status"] == "NOT_REGISTERED"
    manager.writer.state = ChainOperationState.CONFIRMED
    recovered = await client.post(
        f"/v1/operations/{created.json()['registration_operation_id']}/recover"
    )
    assert recovered.json()["status"] == "CONFIRMED"
    assert len([s for s in manager.writer.submissions if s.action == "register_proof"]) == 1
    alias = await client.post(
        f"/v2/issuer/proofs/{identifier}/register",
        json={
            "request_id": "req_registration_alias",
        },
    )
    assert alias.json()["status"] == "CONFIRMED"
    assert len([s for s in manager.writer.submissions if s.action == "register_proof"]) == 1
    manager.writer.state = ChainOperationState.UNKNOWN
    use = await client.post(
        f"/v2/proofs/{identifier}/consume", json={"request_id": "req_uncertain"}
    )
    assert use.json()["status"] == "UNKNOWN"
    with Session(engine) as db:
        assert db.get(OperationRow, use.json()["operation_id"]).recovery_reference
    assert (
        await client.post(
            f"/v2/proofs/{identifier}/consume",
            json={
                "request_id": "req_another_while_pending",
            },
        )
    ).json()["detail"] == "PROOF_OPERATION_PENDING"
    manager.writer.state = ChainOperationState.CONFIRMED
    recovered = await client.post(f"/v1/operations/{use.json()['operation_id']}/recover")
    assert recovered.json()["status"] == "CONFIRMED"
    assert len([s for s in manager.writer.submissions if s.action == "consume_proof"]) == 1
    other = (
        await client.post("/v2/issuer/proofs", json=w3.body(request_id="req_other_proof"))
    ).json()
    assert (
        await client.post(
            f"/v2/proofs/{other['proof_id']}/consume", json={"request_id": "req_uncertain"}
        )
    ).status_code == 409
    assert (
        await client.post(
            f"/v2/issuer/proofs/{other['proof_id']}/register",
            json={
                "request_id": "req_registration_alias",
            },
        )
    ).json()["detail"] == "REQUEST_ID_CONFLICT"
    manager.writer.state = ChainOperationState.FAILED
    failed = await client.post(
        f"/v2/proofs/{other['proof_id']}/consume", json={"request_id": "req_failed"}
    )
    assert failed.json()["status"] == "FAILED"
    assert manager.proof_states[other["proof_id"]].consumed_at is None


async def test_chain_write_never_precedes_operation_persistence(finals, monkeypatch):
    client, manager, _, _, _, _ = finals
    identifier = (await client.post("/v2/issuer/proofs", json=w3.body())).json()["proof_id"]
    submitted = len(manager.writer.submissions)
    original = w3.AsyncSession.commit

    async def fail_commit(self):
        raise RuntimeError("durable reservation failure")

    monkeypatch.setattr(w3.AsyncSession, "commit", fail_commit)
    import pytest

    with pytest.raises(RuntimeError, match="reservation failure"):
        await client.post(f"/v2/proofs/{identifier}/consume", json={"request_id": "req_db_failure"})
    assert len(manager.writer.submissions) == submitted
    monkeypatch.setattr(w3.AsyncSession, "commit", original)
    assert (
        await client.post(f"/v2/proofs/{identifier}/consume", json={"request_id": "req_db_failure"})
    ).json()["status"] == "CONFIRMED"
