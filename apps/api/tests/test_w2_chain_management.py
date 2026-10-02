"""Real SQLite persistence + HTTP, synthetic adapter; live EVM is a separate gate."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain.writer import (
    ChainOperationState,
    ChainWriteResult,
    JsonRpcBlockchainWriter,
    PreparedChainWrite,
)
from originproof_api import chain_management as module
from originproof_api.accounts import current_session
from originproof_api.chain_management import ChainManagement
from originproof_api.database import (
    AccountRow,
    Base,
    IssuerApplicationRow,
    OperationRow,
    SessionRow,
)
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_api.signers import signer_key, verify_signer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DEPLOYMENT = "dep_" + "11" * 32


class AsyncSession:
    def __init__(self, engine):
        self.db = Session(engine, expire_on_commit=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.db.close()

    def add(self, row):
        self.db.add(row)

    async def get(self, *args):
        return self.db.get(*args)

    async def scalar(self, *args):
        return self.db.scalar(*args)

    async def scalars(self, *args):
        return self.db.scalars(*args)

    async def execute(self, *args):
        return self.db.execute(*args)

    async def commit(self):
        self.db.commit()

    async def rollback(self):
        self.db.rollback()

    async def refresh(self, row):
        self.db.refresh(row)


class Writer(JsonRpcBlockchainWriter):
    def __init__(self):
        self.state = ChainOperationState.CONFIRMED
        self.submissions = []
        self.recoveries = []
        self.next_nonce = 0
        self.lose_hash = False

    async def _prepared(self, action, sender, *args, nonce=None):
        async def verify(*_):
            return True

        return PreparedChainWrite(
            action,
            DEPLOYMENT,
            31337,
            sender,
            "0x" + "bb" * 20,
            "0x" + str(args).encode().hex(),
            self.next_nonce if nonce is None else nonce,
            "ref_" + action,
            1,
            verify,
        )

    async def prepare_register_issuer(self, *args, **kwargs):
        return await self._prepared("register_issuer", *args, **kwargs)

    async def prepare_register_key(self, *args, **kwargs):
        return await self._prepared("register_key", *args, **kwargs)

    async def prepare_revoke_key(self, *args, **kwargs):
        return await self._prepared("revoke_key", *args, **kwargs)

    async def prepare_suspend_issuer(self, *args, **kwargs):
        return await self._prepared("suspend_issuer", *args, **kwargs)

    async def prepare_reactivate_issuer(self, *args, **kwargs):
        return await self._prepared("reactivate_issuer", *args, **kwargs)

    async def prepare_revoke_issuer(self, *args, **kwargs):
        return await self._prepared("revoke_issuer", *args, **kwargs)

    async def submit_prepared(self, prepared):
        self.submissions.append(prepared)
        self.next_nonce = prepared.nonce + 1
        return self.result(
            ChainOperationState.UNKNOWN if self.lose_hash else ChainOperationState.SUBMITTED,
            None if self.lose_hash else "0x" + "aa" * 32,
        )

    def result(self, state, tx_hash="0x" + "aa" * 32):
        return ChainWriteResult(
            state,
            DEPLOYMENT,
            31337,
            tx_hash=tx_hash,
            block_number=2,
            block_hash="0x" + "cc" * 32,
            confirmation_count=1,
            reread_block_number=2,
            error_code="RECEIPT_UNKNOWN" if state == "UNKNOWN" else None,
        )

    async def confirm_prepared(self, prepared, tx_hash):
        return self.result(self.state, tx_hash)

    async def recover_prepared(self, prepared, tx_hash=None):
        self.recoveries.append(prepared)
        return self.result(self.state)

    def restore_prepared(self, prepared, reference):
        assert reference == prepared.recovery_reference
        return prepared


@pytest.fixture
async def context(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    account = AccountRow(account_id="acct_operator", username="operator", role="operator")
    issuer = AccountRow(
        account_id="acct_issuer", username="issuer", role="issuer", issuer_id="iss_a"
    )
    other = AccountRow(account_id="acct_other", username="other", role="issuer", issuer_id="iss_b")
    with Session(engine, expire_on_commit=False) as db:
        db.add_all([account, issuer, other])
        for row in (account, issuer, other):
            row.password_hash = "unused"
        db.add(
            IssuerApplicationRow(
                application_id="app_a",
                issuer_id="iss_a",
                issuer_name="Mock A",
                applicant_account_id="acct_issuer",
                status="APPROVED_PENDING_CHAIN",
            )
        )
        db.commit()
    database = SimpleNamespace(session_factory=lambda: AsyncSession(engine))
    manager = ChainManagement.__new__(ChainManagement)
    manager.database = database
    manager.settings = Settings(signer_directory=str(tmp_path / "signers"))
    manager.manifest = SimpleNamespace(
        deployment_id=DEPLOYMENT,
        chain_id=31337,
        roles={"issuer_manager": "0x" + "11" * 20, "issuer_account": "0x" + "22" * 20},
    )
    manager.writer = Writer()
    manager.active = True

    async def active(_):
        if not manager.active:
            raise HTTPException(409, "ISSUER_NOT_ACTIVE")

    manager.active_issuer = active

    async def key_view(row):
        return module.KeyView.model_validate(row)

    manager.key_view = key_view
    lock = asyncio.Lock()

    @asynccontextmanager
    async def local_lock(_):
        async with lock:
            yield

    monkeypatch.setattr(module, "chain_lock", local_lock)
    monkeypatch.setattr(module, "service", lambda _: manager)
    app = create_app(database=database)
    selected = [account]

    async def identity():
        return selected[0], SessionRow(csrf_token="csrf")

    app.dependency_overrides[current_session] = identity
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-CSRF-Token": "csrf"}
    ) as client:
        yield client, manager, selected, (account, issuer, other), engine
    engine.dispose()


async def test_approval_key_rotation_revocation_and_scopes(context):
    client, manager, selected, accounts, engine = context
    body = {"request_id": "req_activate", "reason": "synthetic"}
    path = "/v1/operator/issuer-applications/app_a/activate"
    responses = await asyncio.gather(client.post(path, json=body), client.post(path, json=body))
    assert all(r.status_code == 200 and r.json()["status"] == "CONFIRMED" for r in responses)
    assert len(manager.writer.submissions) == 1
    assert responses[0].json()["operation_id"] == responses[1].json()["operation_id"]
    assert (await client.post(path, json=body | {"reason": "changed"})).status_code == 409
    with Session(engine, expire_on_commit=False) as db:
        assert db.get(IssuerApplicationRow, "app_a").status == "ACTIVE"
    selected[0] = accounts[1]
    now = datetime.now(UTC).replace(microsecond=0)
    key_body = {
        "request_id": "req_key",
        "reason": "synthetic",
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=1)).isoformat(),
    }
    registered = await client.post("/v1/issuer/keys", json=key_body)
    assert registered.status_code == 200 and registered.json()["status"] == "CONFIRMED"
    assert "recovery_reference" not in registered.text and "secret_ref" not in registered.text
    keys = (await client.get("/v1/issuer/keys")).json()
    assert len(keys) == 1 and keys[0]["selected"]
    key_id = keys[0]["key_id"]
    verify_signer(manager.settings.signer_directory, key_id, keys[0]["signer"])
    before = len(manager.writer.submissions)
    assert (await client.post("/v1/issuer/keys", json=key_body)).json() == registered.json()
    assert len(manager.writer.submissions) == before
    selected[0] = accounts[2]
    assert (await client.get(f"/v1/issuer/keys/{key_id}")).status_code == 404
    assert (await client.post(f"/v1/issuer/keys/{key_id}/revoke", json=body)).status_code == 404
    selected[0] = accounts[1]
    second = await client.post("/v1/issuer/keys", json=key_body | {"request_id": "req_second"})
    assert second.json()["status"] == "CONFIRMED"
    keys = (await client.get("/v1/issuer/keys")).json()
    assert sum(k["selected"] for k in keys) == 1 and all(k["status"] == "ACTIVE" for k in keys)
    revoke = await client.post(f"/v1/issuer/keys/{key_id}/revoke", json=body)
    assert revoke.json()["status"] == "CONFIRMED"
    assert (await client.get(f"/v1/issuer/keys/{key_id}")).json()["status"] == "REVOKED"


async def test_unknown_restart_recovery_no_resubmission(context):
    client, manager, _, _, engine = context
    manager.writer.lose_hash = True
    path = "/v1/operator/issuer-applications/app_a/activate"
    response = await client.post(path, json={"request_id": "req_unknown", "reason": "synthetic"})
    assert response.json()["status"] == "UNKNOWN"
    operation_id = response.json()["operation_id"]
    with Session(engine, expire_on_commit=False) as db:
        assert db.get(IssuerApplicationRow, "app_a").status == "APPROVED_PENDING_CHAIN"
        row = db.get(OperationRow, operation_id)
        assert row.recovery_reference["nonce"] == 0 and row.tx_hash is None
    submissions = manager.writer.submissions
    manager.writer = Writer()  # restart loses process-local nonce tracking
    recovered = await client.post(f"/v1/operations/{operation_id}/recover")
    assert recovered.json()["status"] == "CONFIRMED"
    assert len(submissions) == 1 and not manager.writer.submissions
    assert manager.writer.recoveries[0].nonce == 0
    manager.manifest.deployment_id = "dep_" + "ff" * 32
    assert (await client.post(f"/v1/operations/{operation_id}/recover")).status_code == 409


async def test_failed_receipt_permissions_and_unapproved_keys(context):
    client, manager, selected, accounts, engine = context
    manager.writer.state = ChainOperationState.FAILED
    path = "/v1/operator/issuer-applications/app_a/activate"
    body = {"request_id": "req_fail", "reason": "synthetic"}
    result = await client.post(path, json=body)
    assert result.json()["status"] == "FAILED"
    with Session(engine, expire_on_commit=False) as db:
        assert db.get(IssuerApplicationRow, "app_a").status == "APPROVED_PENDING_CHAIN"
    assert (await client.post(path, json=body)).json()["status"] == "FAILED"
    assert len(manager.writer.submissions) == 1
    selected[0] = accounts[1]
    assert (await client.post(path, json=body)).status_code == 403
    manager.active = False
    now = datetime.now(UTC).replace(microsecond=0)
    denied = await client.post(
        "/v1/issuer/keys",
        json=body
        | {"valid_from": now.isoformat(), "valid_until": (now + timedelta(days=1)).isoformat()},
    )
    assert denied.status_code == 409
    assert (
        await client.post(path, json=body, headers={"X-CSRF-Token": "wrong"})
    ).status_code == 403


def test_signer_recovery_permissions_and_missing_key(tmp_path):
    root = tmp_path / "private"
    key = signer_key(str(root), "key_test", create=True)
    address = key.public_key.to_checksum_address()
    assert verify_signer(str(root), "key_test", address).to_bytes() == key.to_bytes()
    with pytest.raises(ValueError):
        verify_signer(str(root), "key_test", "0x" + "aa" * 20)
    (root / "key_test").chmod(0o644)
    with pytest.raises(ValueError):
        signer_key(str(root), "key_test")
    with pytest.raises(OSError):
        signer_key(str(root), "key_missing")
    (root / "key_test").chmod(0o600)
    (root / "key_test").write_bytes(bytes(32))
    with pytest.raises(ValueError):
        signer_key(str(root), "key_test")


async def test_database_failure_after_send_recovers_same_transaction(context, monkeypatch):
    client, manager, _, _, engine = context
    original = manager.confirm_target

    async def fail_final_record(*_):
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(manager, "confirm_target", fail_final_record)
    with pytest.raises(RuntimeError, match="synthetic database failure"):
        await client.post(
            "/v1/operator/issuer-applications/app_a/activate",
            json={"request_id": "req_db_loss", "reason": "synthetic"},
        )
    with Session(engine) as db:
        row = db.scalar(module.select(OperationRow).where(OperationRow.request_id == "req_db_loss"))
        operation_id = row.operation_id
        assert row.status == "SUBMITTED" and row.tx_hash
        assert db.get(IssuerApplicationRow, "app_a").status == "APPROVED_PENDING_CHAIN"
    monkeypatch.setattr(manager, "confirm_target", original)
    recovered = await client.post(f"/v1/operations/{operation_id}/recover")
    assert recovered.json()["status"] == "CONFIRMED"
    assert len(manager.writer.submissions) == 1 and len(manager.writer.recoveries) == 1


async def test_failed_preparation_persistence_never_sends(context, monkeypatch):
    client, manager, _, _, _ = context

    async def fail_prepared(*_):
        raise RuntimeError("synthetic reservation storage failure")

    monkeypatch.setattr(module.OperationPersistence, "save_prepared", fail_prepared)
    with pytest.raises(RuntimeError, match="synthetic reservation storage failure"):
        await client.post(
            "/v1/operator/issuer-applications/app_a/activate",
            json={"request_id": "req_not_sent", "reason": "synthetic"},
        )
    assert not manager.writer.submissions


async def test_restart_respects_unsent_nonce_reservations(context):
    _, manager, _, accounts, engine = context
    with Session(engine) as db:
        db.add(
            OperationRow(
                operation_id="op_reserved",
                account_id=accounts[0].account_id,
                issuer_id="iss_a",
                action="register_issuer",
                request_id="req_reserved",
                input_hash="00" * 32,
                status="PENDING_SUBMISSION",
                deployment_id=DEPLOYMENT,
                recovery_reference={"sender": manager.manifest.roles["issuer_manager"], "nonce": 0},
            )
        )
        db.commit()
    operation = OperationRow(
        operation_id="op_next",
        account_id=accounts[0].account_id,
        issuer_id="iss_a",
        action="register_issuer",
        target_id="app_a",
        input_body={"reason": "synthetic"},
    )
    prepared = await manager.prepare(operation)
    assert prepared.nonce == 1 and not manager.writer.submissions
