from datetime import UTC, datetime
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient
from originproof_api.accounts import password_hash, password_matches
from originproof_api.applications import DecisionInput, decide
from originproof_api.database import (
    AccountRow,
    AuditEventRow,
    Base,
    IssuerApplicationRow,
    SessionRow,
)
from originproof_api.main import create_app
from sqlalchemy import create_engine


def test_passwords_are_salted_and_compared() -> None:
    first = password_hash("synthetic-long-password")
    second = password_hash("synthetic-long-password")
    assert first != second
    assert password_matches("synthetic-long-password", first)
    assert not password_matches("wrong", first)
    assert not password_matches("synthetic-long-password", "malformed")


def test_w1_tables_have_valid_schema() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    assert {"accounts", "account_sessions", "issuer_applications", "audit_events"} <= set(
        Base.metadata.tables
    )
    engine.dispose()


async def test_review_stays_pending_until_chain_confirmation() -> None:
    application = IssuerApplicationRow(
        application_id="app_demo",
        issuer_id="iss_demo",
        applicant_account_id="acct_issuer",
        issuer_name="Synthetic Issuer",
        status="PENDING_REVIEW",
        created_at=datetime.now(UTC),
    )

    class FakeDatabase:
        event: AuditEventRow | None = None

        def session_factory(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def scalar(self, _):
            return application

        def add(self, row):
            if isinstance(row, AuditEventRow):
                self.event = row

        async def commit(self):
            return None

        async def refresh(self, _):
            return None

    database = FakeDatabase()
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(database=database)),
        headers={"X-CSRF-Token": "csrf_test"},
    )
    operator = AccountRow(account_id="acct_operator", username="operator", role="operator")
    session = SessionRow(csrf_token="csrf_test")
    result = await decide(
        "app_demo",
        DecisionInput(decision="APPROVE", reason="synthetic review"),
        request,
        (operator, session),
    )
    assert result.status == "APPROVED_PENDING_CHAIN"
    assert database.event is not None
    assert database.event.after_status == "APPROVED_PENDING_CHAIN"


async def test_management_endpoints_require_login() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/v1/auth/me")).status_code == 401
        assert (await client.get("/v1/issuer-applications/mine")).status_code == 401


async def test_login_csrf_logout_flow() -> None:
    class FakeDatabase:
        def __init__(self) -> None:
            self.account = AccountRow(
                account_id="acct_test",
                username="demo-issuer",
                password_hash=password_hash("synthetic-long-password"),
                role="issuer",
                issuer_id="iss_demo",
            )
            self.session: SessionRow | None = None

        def session_factory(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def scalar(self, _):
            return self.account

        async def get(self, model, _):
            return self.session if model is SessionRow else self.account

        def add(self, row):
            if isinstance(row, SessionRow):
                self.session = row

        async def delete(self, _):
            self.session = None

        async def commit(self):
            return None

    app = create_app()
    app.state.database = FakeDatabase()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post(
            "/v1/auth/login",
            json={"username": "demo-issuer", "password": "synthetic-long-password"},
        )
        assert login.status_code == 200
        assert "httponly" in login.headers["set-cookie"].lower()
        assert (await client.get("/v1/auth/me")).json()["issuer_id"] == "iss_demo"
        assert (await client.post("/v1/auth/logout")).status_code == 403
        logout = await client.post(
            "/v1/auth/logout", headers={"X-CSRF-Token": login.json()["csrf_token"]}
        )
        assert logout.status_code == 200
        assert (await client.get("/v1/auth/me")).status_code == 401
