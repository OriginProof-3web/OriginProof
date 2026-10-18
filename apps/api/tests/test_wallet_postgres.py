"""Opt-in disposable PostgreSQL concurrency; chain evidence remains synthetic."""

import asyncio
import os
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from originproof_api.accounts import current_session
from originproof_api.database import AccountRow, Database, IssuerApplicationRow, OperationRow
from originproof_api.main import create_app
from originproof_api.settings import Settings
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from test_wallet_analyses import input_ref, report, settle
from test_wallet_runtime import APPROVERS, DOMAIN, ISSUER, Chain, activated, draft, sign

pytestmark = pytest.mark.skipif(
    not os.environ.get("V5_C_TEST_DATABASE_URL"),
    reason="requires a fresh disposable PostgreSQL database",
)


async def test_real_postgres_serializes_publication_and_analysis_requests():
    raw = os.environ["V5_C_TEST_DATABASE_URL"]
    url = make_url(raw)
    assert url.host == "127.0.0.1" and url.database.startswith("originproof_v5_c_test_")
    database = Database(raw)
    accounts = {
        "issuer": AccountRow(account_id="acct_i", username="i", role="issuer", issuer_id=ISSUER),
        "internal": AccountRow(
            account_id="acct_internal", username="in", role="issuer", issuer_id=ISSUER
        ),
        "operator": AccountRow(account_id="acct_o", username="o", role="operator"),
        "recipient": AccountRow(account_id="acct_r", username="r", role="recipient"),
        "office": AccountRow(
            account_id="acct_office",
            username="off",
            role="issuer",
            issuer_id="iss_origin_mock_office",
        ),
    }
    async with database.session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(AccountRow)) == 0, (
            "fresh DB required"
        )
        for row in accounts.values():
            row.password_hash = "synthetic-unused"
            db.add(row)
        db.add(
            IssuerApplicationRow(
                application_id="app_test",
                issuer_id=ISSUER,
                applicant_account_id="acct_i",
                issuer_name="Origin Mock Bank",
                status="PENDING_REVIEW",
            )
        )
        await db.commit()
    settings = Settings(
        _env_file=None,
        projection_enabled=False,
        finals_payment_issuer_id=ISSUER,
        finals_document_issuer_id="iss_origin_mock_office",
        wallet_registry_address=DOMAIN.verifying_contract,
        wallet_operator_addresses={"acct_o": APPROVERS[0]},
        wallet_internal_approvers={ISSUER: "acct_internal"},
        wallet_demo_email_enabled=True,
        wallet_email_secret="synthetic-wallet-postgres-email-secret-for-tests-only",
        wallet_text_input_enabled=True,
    )
    chain = Chain()
    app = create_app(database=database, settings=settings, wallet_chain=chain)
    who = {"name": "issuer"}

    async def identity():
        return accounts[who["name"]], SimpleNamespace(csrf_token="csrf")

    app.dependency_overrides[current_session] = identity
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-CSRF-Token": "csrf"},
        ) as client:
            w = SimpleNamespace(client=client, app=app, who=who, chain=chain)
            await activated(w)
            first, second = await draft(w), await draft(w, request_id="req_other_draft")
            bodies = [
                {
                    "request_id": "req_race_" + str(i),
                    "signing_request_id": value["signing_request_id"],
                    "signature": sign(value),
                }
                for i, value in enumerate((first, second))
            ]
            result = await asyncio.gather(
                *(client.post("/v3/publications", json=b) for b in bodies)
            )
            assert sorted(r.status_code for r in result) == [202, 409], [r.text for r in result]
            async with database.session_factory() as db:
                assert (
                    await db.scalar(
                        select(func.count())
                        .select_from(OperationRow)
                        .where(OperationRow.action == "wallet_publish")
                    )
                    == 1
                )
            started, release = asyncio.Event(), asyncio.Event()
            calls = []

            async def delayed(text):
                calls.append(True)
                started.set()
                await release.wait()
                return report(text)

            app.state.analysis_processor = delayed
            source1, source2 = await input_ref(w), await input_ref(w)
            candidates = [
                {"request_id": "req_jobs_" + str(i), "input_ref": source}
                for i, source in enumerate((source1, source2))
            ]
            responses = await asyncio.gather(
                *(client.post("/v3/analyses", json=b) for b in candidates)
            )
            assert sorted(r.status_code for r in responses) == [202, 429], [
                r.text for r in responses
            ]
            await asyncio.wait_for(started.wait(), timeout=3)
            release.set()
            await settle(w)
            assert len(calls) == 1 and not chain.sends
            assert (await client.get("/health/ready")).status_code == 200
    finally:
        for task in list(app.state.analysis_tasks):
            task.cancel()
        await asyncio.gather(*list(app.state.analysis_tasks), return_exceptions=True)
        await database.dispose()
