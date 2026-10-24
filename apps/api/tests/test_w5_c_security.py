"""W5-C1 real HTTP guard checks plus existing SQLite/adapter authorization checks."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import test_w2_chain_management as w2_tests
from httpx import ASGITransport, AsyncClient
from originproof_api.database import AuditEventRow, OperationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from sqlalchemy.orm import Session

context = w2_tests.context


def mutations():
    change = {"request_id": "req_security", "reason": "synthetic security check"}
    now = datetime.now(UTC).replace(microsecond=0)
    key = change | {
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(days=1)).isoformat(),
    }
    return [
        ("/v1/issuer-applications", {"issuer_name": "Mock A"}, 1),
        (
            "/v1/operator/issuer-applications/app_a/decision",
            {"decision": "APPROVE", "reason": "synthetic"},
            0,
        ),
        ("/v1/operator/issuer-applications/app_a/activate", change, 0),
        *[
            (f"/v1/operator/issuers/iss_a/{action}", change, 0)
            for action in ("suspend", "reactivate", "revoke")
        ],
        ("/v1/issuer/keys", key, 1),
        ("/v1/issuer/keys/rotate", key, 1),
        ("/v1/issuer/keys/key_a/revoke", change, 1),
        ("/v1/operations/op_a/recover", {}, 1),
        ("/v1/auth/logout", {}, 1),
        (
            "/v2/issuer/proofs",
            {
                "request_id": "req_security",
                "recipient_id": "acct_recipient",
                "expires_at": (now + timedelta(days=1)).isoformat(),
                "content": {
                    "proof_type": "PAYMENT_REQUEST",
                    "amount_minor": 100,
                    "currency": "KRW",
                    "target_ref": "synthetic",
                },
            },
            1,
        ),
    ]


@pytest.mark.parametrize("path,body,actor", mutations())
async def test_every_existing_state_change_checks_csrf(context, path, body, actor):
    client, manager, selected, accounts, _ = context
    selected[0] = accounts[actor]
    for token in ("", "wrong"):
        response = await client.post(path, json=body, headers={"X-CSRF-Token": token})
        assert response.status_code == 403 and response.json()["detail"] == "CSRF_REQUIRED"
    assert not manager.writer.submissions


def test_request_budget_expires_and_storage_stays_bounded(monkeypatch):
    from originproof_api import security

    clock = [0]
    monkeypatch.setattr(security, "monotonic", lambda: clock[0])
    guard = security.RequestSecurity(None, Settings(requests_per_minute=1))
    assert guard.allowance("peer", False) == 0
    assert guard.allowance("peer", False) == 60
    clock[0] = 60
    assert guard.allowance("peer", False) == 0
    for i in range(4095):
        assert guard.allowance(str(i), False) == 0
    assert guard.allowance("over-capacity", False) == 60
    assert len(guard.buckets) == 4096


async def test_slow_body_times_out_without_running_endpoint():
    app = create_app(settings=Settings(request_body_timeout_seconds=1))

    async def slow_body():
        yield b"{"
        await asyncio.sleep(2)
        yield b"}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/auth/login", content=slow_body())
        assert response.status_code == 408
        assert response.json() == {"error": "REQUEST_TIMEOUT"}


async def test_request_budget_is_shared_across_paths_and_forwarded_headers():
    app = create_app(settings=Settings(requests_per_minute=2))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        replies = await asyncio.gather(
            client.get("/v1/auth/me", headers={"X-Forwarded-For": "1.1.1.1"}),
            client.get("/v2/issuer/proofs", headers={"X-Forwarded-For": "2.2.2.2"}),
            client.get("/v1/audit-events", headers={"X-Forwarded-For": "3.3.3.3"}),
        )
        assert sorted(r.status_code for r in replies) == [401, 401, 429]
        limited = next(r for r in replies if r.status_code == 429)
        assert limited.json() == {"error": "RATE_LIMITED"}
        assert 1 <= int(limited.headers["Retry-After"]) <= 60
        assert limited.headers["Cache-Control"] == "no-store"
        assert (await client.get("/health/live")).status_code == 200


async def test_login_has_separate_budget_and_origin_check():
    app = create_app(settings=Settings(logins_per_minute=2))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for origin in ("https://untrusted.example", "null"):
            response = await client.post("/v1/auth/login", headers={"Origin": origin}, json={})
            assert response.status_code == 403
            assert response.json() == {"error": "ORIGIN_FORBIDDEN"}
        assert (await client.post("/v1/auth/login", json={})).status_code == 429
        assert (await client.get("/v1/auth/me")).status_code == 401


async def test_origin_allowlist_and_cross_site_fallback():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for headers in ({}, {"Origin": "http://localhost:3000"}):
            response = await client.post("/v1/auth/login", headers=headers, json={})
            assert response.status_code == 422
        for headers in (
            {"Origin": "http://localhost:3000.attacker.example"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            response = await client.post("/v1/auth/login", headers=headers, json={})
            assert response.status_code == 403


async def test_body_limit_checks_declared_and_streamed_size():
    app = create_app(settings=Settings(request_body_max_bytes=1024))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for length, expected in (("1025", 413), ("9" * 5000, 413), ("invalid", 400)):
            response = await client.post(
                "/v1/auth/login", content=b"{}", headers={"Content-Length": length}
            )
            assert response.status_code == expected

        async def chunks():
            yield b"x" * 600
            yield b"x" * 600

        response = await client.post("/v1/auth/login", content=chunks())
        assert response.status_code == 413
        assert response.json() == {"error": "REQUEST_TOO_LARGE"}
        assert (await client.post("/v1/auth/login", content=b"x" * 1024)).status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/v1/issuer-applications",
        "/v1/operator/issuer-applications/app_a/decision",
        "/v1/operator/issuer-applications/app_a/activate",
        "/v1/operator/issuers/iss_a/suspend",
        "/v1/operator/issuers/iss_a/reactivate",
        "/v1/operator/issuers/iss_a/revoke",
        "/v1/issuer/keys",
        "/v1/issuer/keys/rotate",
        "/v1/issuer/keys/key_a/revoke",
        "/v1/operations/op_a/recover",
        "/v2/issuer/proofs",
        "/v1/auth/logout",
    ],
)
async def test_every_existing_state_change_requires_a_session(path):
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(path, json={})).status_code == 401


async def test_operation_and_audit_scope_excludes_other_institution(context):
    client, _, selected, accounts, engine = context
    with Session(engine) as db:
        for issuer in accounts[1:]:
            db.add(
                OperationRow(
                    operation_id="op_" + issuer.account_id,
                    account_id=issuer.account_id,
                    issuer_id=issuer.issuer_id,
                    action="register_key",
                    request_id="req_test",
                    input_hash="0" * 64,
                    status="UNKNOWN",
                    recovery_reference={"private_marker": "server-only"},
                )
            )
            db.add(
                AuditEventRow(
                    event_id="evt_" + issuer.account_id,
                    actor_account_id=issuer.account_id,
                    issuer_id=issuer.issuer_id,
                    action="register_key",
                    target_id="key_test",
                    after_status="UNKNOWN",
                )
            )
        db.commit()
    selected[0] = accounts[1]
    own = await client.get("/v1/operations/op_" + accounts[1].account_id)
    assert own.status_code == 200 and "private_marker" not in own.text
    assert (await client.get("/v1/operations/op_" + accounts[2].account_id)).status_code == 404
    audit = await client.get("/v1/audit-events")
    assert audit.status_code == 200
    assert {row["issuer_id"] for row in audit.json()} == {accounts[1].issuer_id}
