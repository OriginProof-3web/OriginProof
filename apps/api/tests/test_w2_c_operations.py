import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from originproof_api.database import AccountRow, Base, OperationRow
from originproof_api.main import create_app
from originproof_api.operations import input_fingerprint, reserve_operation
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def test_request_reservation_is_unique_per_actor_and_action() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(AccountRow(account_id="acct_a", username="a", password_hash="x", role="issuer"))
        db.add(
            OperationRow(
                operation_id="op_a",
                account_id="acct_a",
                action="ISSUER_ACTIVATE",
                request_id="req_same",
                input_hash=input_fingerprint({"issuer_id": "iss_a"}),
                status="PENDING_SUBMISSION",
            )
        )
        db.commit()
        db.add(
            OperationRow(
                operation_id="op_b",
                account_id="acct_a",
                action="ISSUER_ACTIVATE",
                request_id="req_same",
                input_hash=input_fingerprint({"issuer_id": "iss_b"}),
                status="PENDING_SUBMISSION",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    engine.dispose()


def test_body_fingerprint_ignores_key_order() -> None:
    assert input_fingerprint({"issuer_id": "iss_a", "action": "activate"}) == input_fingerprint(
        {"action": "activate", "issuer_id": "iss_a"}
    )
    assert input_fingerprint({"issuer_id": "iss_a"}) != input_fingerprint({"issuer_id": "iss_b"})


async def test_retry_returns_existing_and_rejects_changed_input() -> None:
    account = AccountRow(account_id="acct_a", issuer_id="iss_a")
    existing = OperationRow(
        operation_id="op_a",
        account_id="acct_a",
        issuer_id="iss_a",
        action="ISSUER_ACTIVATE",
        request_id="req_same",
        input_hash=input_fingerprint({"issuer_id": "iss_a"}),
        status="PENDING_SUBMISSION",
    )

    class DuplicateSession:
        def __call__(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        def add(self, _):
            return None

        async def commit(self):
            raise IntegrityError("insert", {}, Exception("duplicate"))

        async def rollback(self):
            return None

        async def scalar(self, _):
            return existing

    factory = DuplicateSession()
    same = await reserve_operation(
        factory, account, "ISSUER_ACTIVATE", "req_same", {"issuer_id": "iss_a"}
    )
    assert same is existing
    with pytest.raises(HTTPException) as invalid:
        await reserve_operation(factory, account, "ISSUER_ACTIVATE", "bad", {"issuer_id": "iss_a"})
    assert invalid.value.status_code == 422
    with pytest.raises(HTTPException) as error:
        await reserve_operation(
            factory, account, "ISSUER_ACTIVATE", "req_same", {"issuer_id": "iss_b"}
        )
    assert error.value.status_code == 409


async def test_operation_and_audit_queries_require_login() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/v1/operations/op_test")).status_code == 401
        assert (await client.get("/v1/audit-events")).status_code == 401
