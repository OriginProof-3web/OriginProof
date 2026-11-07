"""W4-C1: new issuing key, historical signature policy, failure and concurrency."""

import asyncio
from datetime import UTC, datetime, timedelta

import test_finals_proofs as w3_tests
from originproof_api.database import FinalsProofRow, IssuerKeyRow
from originproof_core.finals import FinalsSignedProofEnvelope
from originproof_core.signatures import signature_matches
from sqlalchemy import select
from sqlalchemy.orm import Session

finals = w3_tests.finals
context = w3_tests.context


def rotation_body(request_id="req_rotation"):
    now = datetime.now(UTC).replace(microsecond=0)
    return {
        "request_id": request_id,
        "reason": "synthetic normal rotation",
        "valid_from": (now - timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timedelta(days=1)).isoformat(),
    }


async def test_rotation_old_proof_survives_new_issue_and_revocation(finals, monkeypatch):
    client, manager, _, _, _, engine = finals
    old = await client.post("/v2/issuer/proofs", json=w3_tests.body())
    old_id, old_key = old.json()["proof_id"], old.json()["key_id"]
    rotated = await client.post("/v1/issuer/keys/rotate", json=rotation_body())
    assert rotated.status_code == 200 and rotated.json()["status"] == "CONFIRMED"
    new = await client.post("/v2/issuer/proofs", json=w3_tests.body(request_id="req_new_issue"))
    assert new.status_code == 200 and new.json()["key_id"] != old_key
    historical = await client.post(f"/v2/proofs/{old_id}/verify", json={"request_id": "req_old"})
    assert historical.json()["verification_status"] == "VERIFIED"
    assert not historical.json()["reason_codes"]
    with Session(engine) as db:
        envelope = FinalsSignedProofEnvelope.model_validate(db.get(FinalsProofRow, old_id).envelope)
        key = db.get(IssuerKeyRow, old_key)
        assert not key.selected and key.status == "ACTIVE"
        assert signature_matches(envelope, key.signer)
        # Ending the issuing period after issuance does not revoke a historical signature.
        key.valid_until = int(envelope.issued_at.timestamp()) + 1
        db.commit()
    from functools import partial

    from originproof_api import finals_proofs

    monkeypatch.setattr(
        finals_proofs,
        "evaluate_finals",
        partial(finals_proofs.evaluate_finals, now=envelope.issued_at + timedelta(seconds=2)),
    )
    historical = await client.post(f"/v2/proofs/{old_id}/verify", json={"request_id": "req_ended"})
    assert historical.json()["verification_status"] == "VERIFIED"
    await client.post(
        f"/v1/issuer/keys/{old_key}/revoke",
        json={"request_id": "req_compromise", "reason": "synthetic compromise"},
    )
    historical = await client.post(
        f"/v2/proofs/{old_id}/verify", json={"request_id": "req_revoked"}
    )
    assert historical.json()["verification_status"] == "VERIFIED"
    assert "ISSUER_KEY_REVOKED" in historical.json()["reason_codes"]
    assert historical.json()["checks"]["proof_status"] == "PASS"
    manager.settings.signer_directory = "/nonexistent-synthetic-signer-directory"
    assert (
        await client.post("/v2/issuer/proofs", json=w3_tests.body(request_id="req_missing_signer"))
    ).status_code == 409


async def test_rotation_failure_future_registration_and_concurrent_issuance(finals):
    client, manager, _, _, _, engine = finals
    with Session(engine) as db:
        old_key = db.scalar(select(IssuerKeyRow).where(IssuerKeyRow.issuer_id == "iss_a"))
        old_id = old_key.key_id
    now = datetime.now(UTC).replace(microsecond=0)
    future = rotation_body("req_future") | {
        "valid_from": (now + timedelta(hours=1)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
    }
    assert (await client.post("/v1/issuer/keys/rotate", json=future)).status_code == 422
    # The existing registration endpoint can prepare a future key, but must retain the current key.
    assert (await client.post("/v1/issuer/keys", json=future)).json()["status"] == "CONFIRMED"
    with Session(engine) as db:
        assert db.get(IssuerKeyRow, old_id).selected
    from infrastructure.blockchain.writer import ChainOperationState

    manager.writer.state = ChainOperationState.FAILED
    response = await client.post("/v1/issuer/keys/rotate", json=rotation_body("req_failed"))
    assert response.json()["status"] == "FAILED"
    with Session(engine) as db:
        assert db.get(IssuerKeyRow, old_id).selected
    manager.writer.state = ChainOperationState.CONFIRMED
    responses = await asyncio.gather(
        client.post("/v1/issuer/keys/rotate", json=rotation_body("req_parallel")),
        client.post("/v2/issuer/proofs", json=w3_tests.body(request_id="req_parallel_issue")),
    )
    assert all(response.status_code == 200 for response in responses)
    with Session(engine) as db:
        selected = list(
            db.scalars(
                select(IssuerKeyRow).where(
                    IssuerKeyRow.issuer_id == "iss_a", IssuerKeyRow.selected.is_(True)
                )
            )
        )
        assert len(selected) == 1
    assert (
        await client.post(
            "/v1/issuer/keys/rotate", json=rotation_body("req_parallel") | {"reason": "changed"}
        )
    ).status_code == 409


async def test_late_recovery_does_not_undo_a_newer_key_rotation(finals):
    from infrastructure.blockchain.writer import ChainOperationState

    client, manager, _, _, _, engine = finals
    manager.writer.state = ChainOperationState.UNKNOWN
    older = await client.post("/v1/issuer/keys/rotate", json=rotation_body("req_older_unknown"))
    assert older.json()["status"] == "UNKNOWN"
    manager.writer.state = ChainOperationState.CONFIRMED
    newer = await client.post("/v1/issuer/keys/rotate", json=rotation_body("req_newer_confirmed"))
    assert newer.json()["status"] == "CONFIRMED"
    recovered = await client.post(f"/v1/operations/{older.json()['operation_id']}/recover")
    assert recovered.json()["status"] == "CONFIRMED"
    with Session(engine) as db:
        selected = list(
            db.scalars(
                select(IssuerKeyRow).where(
                    IssuerKeyRow.issuer_id == "iss_a", IssuerKeyRow.selected.is_(True)
                )
            )
        )
        assert len(selected) == 1 and selected[0].key_id == newer.json()["target_id"]
    assert len(manager.writer.submissions) == 4  # two fixture registrations + two rotations
