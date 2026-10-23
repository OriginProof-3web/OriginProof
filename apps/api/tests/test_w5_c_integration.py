"""W5 scopes and recovery guidance on real persisted rows; chain is synthetic here."""

import os
from datetime import UTC, datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import test_finals_proofs as w3
from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain.writer import ChainOperationState
from originproof_api.database import AuditEventRow
from originproof_api.main import create_app
from originproof_api.projection import SyncView
from sqlalchemy.orm import Session

context = w3.context
finals = w3.finals


async def test_lifecycle_operation_audit_scopes_and_guidance(finals):
    client, manager, selected, accounts, _, engine = finals
    manager.writer.state = ChainOperationState.UNKNOWN
    proof = (await client.post("/v2/issuer/proofs", json=w3.body())).json()
    operation_id = proof["registration_operation_id"]
    operation = await client.get(f"/v1/operations/{operation_id}")
    assert operation.json()["recovery_required"]
    assert operation.json()["next_action"] == "RECOVER_SAME_OPERATION"
    rows = (await client.get("/v1/operations", params={"target_id": proof["proof_id"]})).json()
    assert len(rows) == 1 and rows[0]["operation_id"] == operation_id
    assert "recovery_reference" not in str(rows) and "input_body" not in str(rows)
    with Session(engine) as db:
        db.add(
            AuditEventRow(
                event_id="evt_other",
                actor_account_id=accounts[2].account_id,
                issuer_id=accounts[2].issuer_id,
                action="synthetic",
                target_id=proof["proof_id"],
                before_status=None,
                after_status="PENDING_SUBMISSION",
            )
        )
        db.commit()
    audit = (await client.get("/v1/audit-events", params={"target_id": proof["proof_id"]})).json()
    assert audit and all(row["issuer_id"] == accounts[1].issuer_id for row in audit)
    assert (await client.get("/v1/audit-events?limit=201")).status_code == 422
    selected[0] = accounts[2]
    assert (await client.get(f"/v1/operations/{operation_id}")).status_code == 404
    assert (
        await client.get("/v1/operations", params={"target_id": proof["proof_id"]})
    ).json() == []
    assert (await client.get("/v1/audit-events", params={"target_id": proof["proof_id"]})).json()[
        0
    ]["event_id"] == "evt_other"
    selected[0] = accounts[1]
    manager.writer.state = ChainOperationState.CONFIRMED
    recovered = await client.post(f"/v1/operations/{operation_id}/recover")
    assert recovered.json()["next_action"] == "NONE"
    assert not recovered.json()["recovery_required"]


async def test_sync_status_never_exposes_stale_projection_as_current(finals):
    client, _, selected, accounts, recipients, _ = finals
    app = client._transport.app
    app.state.projection = SyncView(
        status="SYNCED", checked_at=datetime.now(UTC) - timedelta(hours=1)
    )
    response = await client.get("/v1/chain-sync")
    assert response.json()["status"] == "STALE"
    assert response.json()["authority"] == "HISTORICAL_EVENTS_ONLY"
    selected[0] = recipients[0]
    assert (await client.get("/v1/chain-sync")).status_code == 403
    selected[0] = accounts[0]
    assert (await client.get("/v1/chain-sync")).status_code == 200


async def test_not_prepared_runtime_is_503_without_sensitive_errors():
    class Unavailable:
        session_factory = None

        async def ping(self):
            raise RuntimeError("synthetic database password must not appear")

    app = create_app(database=Unavailable())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "RUNTIME_NOT_READY"}
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/v1/chain-sync")).status_code == 401


def test_local_seed_password_is_preserved_and_links_are_rejected(tmp_path):
    spec = spec_from_file_location(
        "seed_accounts", Path(__file__).parents[3] / "scripts/fixtures/seed_accounts.py"
    )
    seed = module_from_spec(spec)
    spec.loader.exec_module(seed)
    path = tmp_path / "credentials.json"
    first = seed.synthetic_password(path)
    assert seed.synthetic_password(path) == first
    assert path.stat().st_mode & 0o777 == 0o600
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(OSError):
        seed.synthetic_password(link)
    hard = tmp_path / "hard"
    os.link(path, hard)
    with pytest.raises(ValueError, match="unsafe"):
        seed.synthetic_password(path)

    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="unsafe"):
        seed.synthetic_password(fifo)


async def test_v5_wallet_seed_is_idempotent_and_prints_roster_mapping(monkeypatch):
    import json

    from originproof_api.database import AccountRow, Base
    from sqlalchemy import create_engine, select
    from test_w2_chain_management import AsyncSession

    spec = spec_from_file_location(
        "seed_accounts", Path(__file__).parents[3] / "scripts/fixtures/seed_accounts.py"
    )
    seed = module_from_spec(spec)
    spec.loader.exec_module(seed)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    class Database:
        def __init__(self, _url):
            self.session_factory = lambda: AsyncSession(engine)

        async def dispose(self):
            pass

    monkeypatch.setattr(seed, "Database", Database)
    first = await seed.seed_prepared(seed.V5_WALLET_ACCOUNTS, "synthetic-password-1")
    assert await seed.seed_prepared(seed.V5_WALLET_ACCOUNTS, "other-password-12") == first
    env = dict(line.split("=", 1) for line in seed.v5_wallet_env(first))
    assert json.loads(env["API_WALLET_INTERNAL_APPROVERS"]) == {
        "iss_origin_mock_bank": first["v5_bank_approver"],
        "iss_origin_mock_office": first["v5_office_approver"],
    }
    assert set(json.loads(env["API_WALLET_OPERATOR_ADDRESSES"])) == {
        first[f"v5_operator{n}"] for n in (1, 2, 3)
    }
    with Session(engine) as db:
        row = db.scalar(select(AccountRow).where(AccountRow.username == "v5_operator1"))
        row.role = "recipient"
        db.commit()
    with pytest.raises(ValueError, match="identity differs"):
        await seed.seed_prepared(seed.V5_WALLET_ACCOUNTS, "synthetic-password-1")


async def test_reconciliation_separates_db_confirmation_from_live_chain(finals):
    client, manager, selected, accounts, _, _ = finals
    proof = (await client.post("/v2/issuer/proofs", json=w3.body())).json()
    path = f"/v2/issuer/proofs/{proof['proof_id']}/reconciliation"
    response = await client.get(path)
    assert response.json()["database_registration_status"] == "CONFIRMED"
    assert response.json()["registration_consistent"] is True
    assert response.json()["authority"] == "CANONICAL_READER"
    assert "payload" not in response.json()
    selected[0] = accounts[2]
    assert (await client.get(path)).status_code == 404
    selected[0] = accounts[1]
    saved = manager.proof_states.pop(proof["proof_id"])
    response = await client.get(path)
    assert response.json()["database_registration_status"] == "CONFIRMED"
    assert response.json()["registration_consistent"] is False
    assert response.json()["current_verification"]["verification_status"] == "NOT_REGISTERED"
    manager.proof_states[proof["proof_id"]] = saved
    manager.rpc_failure = True
    response = await client.get(path)
    assert response.json()["registration_consistent"] is None
    assert response.json()["current_verification"]["verification_status"] == "INCONCLUSIVE"
