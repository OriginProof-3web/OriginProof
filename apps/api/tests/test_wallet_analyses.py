"""Storage/ownership/grounding fences with a synthetic processor, no paid AI claims."""

import asyncio
import time
from datetime import UTC, datetime, timedelta

import pytest
from originproof_api import wallet_analyses as module
from originproof_api.wallet_database import WalletAnalysisRow, WalletInputRow
from sqlalchemy.orm import Session
from test_wallet_runtime import activated, confirmed_publication, confirmed_revocation, draft

pytest_plugins = ("test_wallet_runtime",)


def report(text, risk="CAUTION"):
    return {
        "risk_level": risk,
        "evidence": [
            {
                "rule_id": "SYNTHETIC",
                "quote": text[:3],
                "start_offset": 0,
                "end_offset": 3,
                "source": "RULE",
            }
        ],
        "limitations": ["synthetic processor"],
        "verification_not_run_reason": "NO_DOCUMENT_REFERENCE",
    }


async def processor(text):
    return report(text)


async def input_ref(w, text="💡송금 확인은 공식 창구에서 하세요"):
    response = await w.client.post("/v3/inputs", json={"kind": "TEXT", "text": text})
    assert response.status_code == 201, response.text
    return response.json()["input_ref"]


async def settle(w):
    pending = list(w.app.state.analysis_tasks)
    if pending:
        await asyncio.gather(*pending)
    assert w.app.state.analysis_worker_error is None


@pytest.mark.parametrize("text", ["하하하", "💡하하하"])
def test_ambiguous_overlapping_quotes_require_an_explicit_location(text):
    candidate = report(text)
    candidate["evidence"][0] = {"rule_id": "SYNTHETIC", "quote": "하하", "source": "RULE"}
    with pytest.raises(ValueError, match="GROUNDING_MISMATCH"):
        module.ground_report(candidate, text)


@pytest.mark.parametrize("start", [0, 1])
def test_overlapping_quotes_with_exact_offsets_are_allowed(start):
    candidate = report("하하하")
    candidate["evidence"][0].update(quote="하하", start_offset=start, end_offset=start + 2)
    result = module.ground_report(candidate, "하하하")
    assert result.evidence[0].start_offset == start


def test_unique_quote_location_uses_unicode_code_points():
    candidate = report("💡 앞부분 인용")
    candidate["evidence"][0] = {"rule_id": "SYNTHETIC", "quote": "인용", "source": "RULE"}
    value = module.ground_report(candidate, "💡 앞부분 인용")
    assert (value.evidence[0].start_offset, value.evidence[0].end_offset) == (6, 8)


async def test_retention_preserves_legacy_and_unresolved_audit_records(wallet):
    from originproof_api.database import AuditEventRow, OperationRow
    from originproof_api.wallet_database import WalletRequestRow

    stamp = int(time.time())
    old = datetime.fromtimestamp(stamp, UTC) - timedelta(days=31)
    cases = [
        ("old", "wallet_publish", "CONFIRMED", stamp - 31 * 86400),
        ("unknown", "wallet_publish", "UNKNOWN", None),
        ("recent", "wallet_publish", "CONFIRMED", stamp - 86400),
        ("legacy", "publish", "CONFIRMED", stamp - 31 * 86400),
        ("lookalike", "walletXpublish", "CONFIRMED", stamp - 31 * 86400),
    ]
    with Session(wallet.engine) as db:
        for name, action, status, resolved in cases:
            db.add(
                OperationRow(
                    operation_id="op_" + name,
                    account_id="acct_i",
                    issuer_id="iss_origin_mock_bank",
                    action=action,
                    request_id="req_" + name,
                    input_hash="0" * 64,
                    status=status,
                    input_body={},
                    target_id="target_" + name,
                    recovery_reference={"resolved_at": resolved},
                    created_at=old,
                )
            )
            db.add(
                AuditEventRow(
                    event_id="evt_" + name,
                    actor_account_id="acct_i",
                    action=action,
                    target_id="target_" + name,
                    after_status=status,
                    created_at=old,
                )
            )
        db.add(
            AuditEventRow(
                event_id="evt_orphan",
                actor_account_id="acct_i",
                action="wallet_analysis",
                target_id="ana_orphan",
                after_status="FAILED",
                created_at=old,
            )
        )
        db.add(
            WalletRequestRow(
                account_id="acct_i",
                action="Publish",
                request_id="req_old_claim",
                input_hash="0" * 64,
                resource_id="op_old",
            )
        )
        db.commit()
    await module.cleanup(wallet.app)
    with Session(wallet.engine) as db:
        assert db.get(OperationRow, "op_old") is None
        assert db.get(AuditEventRow, "evt_old") is None
        assert db.get(AuditEventRow, "evt_orphan") is None
        assert db.get(WalletRequestRow, ("acct_i", "Publish", "req_old_claim")) is None
        for name in ("unknown", "recent", "legacy", "lookalike"):
            assert db.get(OperationRow, "op_" + name) is not None
            assert db.get(AuditEventRow, "evt_" + name) is not None


async def test_retained_revocation_retries_return_gone_after_actual_cleanup(wallet, monkeypatch):
    from originproof_api.database import OperationRow
    from originproof_api.wallet_database import WalletRequestRow, WalletSigningRow
    from sqlalchemy import select

    await activated(wallet)
    doc, _ = await confirmed_publication(wallet, await draft(wallet))
    operation = await confirmed_revocation(wallet, doc.document_id, 1)
    with Session(wallet.engine) as db:
        row = db.scalar(select(WalletSigningRow).where(WalletSigningRow.kind == "Revoke"))
        signing_id, signature = row.signing_request_id, row.signature
    alias = {
        "request_id": "req_retained_alias",
        "signing_request_id": signing_id,
        "signature": signature,
    }
    retry = await wallet.client.post("/v3/revocations", json=alias)
    assert retry.status_code == 202, retry.text
    future = int(time.time()) + 31 * 86400
    monkeypatch.setattr(module, "now", lambda: future)
    await module.cleanup(wallet.app)
    with Session(wallet.engine) as db:
        assert db.get(OperationRow, operation["operation_id"]) is None
        assert db.get(WalletSigningRow, signing_id).signature == signature
        assert (
            list(
                db.scalars(
                    select(WalletRequestRow).where(
                        WalletRequestRow.resource_id == operation["operation_id"]
                    )
                )
            )
            == []
        )
    for request_id in (alias["request_id"], "req_after_cleanup"):
        expired = await wallet.client.post(
            "/v3/revocations", json={**alias, "request_id": request_id}
        )
        assert expired.status_code == 410 and expired.json()["detail"] == "RESULT_EXPIRED"
    direct = await wallet.client.post(
        f"/v3/signing-requests/{signing_id}/transactions",
        json={
            "request_id": "req_expired_direct",
            "signing_request_id": signing_id,
            "tx_hash": operation["tx_hash"],
        },
    )
    assert direct.status_code == 410 and direct.json()["detail"] == "RESULT_EXPIRED"


async def test_analysis_request_only_expires_own_jobs_and_maintenance_handles_the_rest(wallet):
    from originproof_api.database import AuditEventRow

    stamp = int(time.time())
    wallet.app.state.settings.wallet_text_input_enabled = True
    wallet.app.state.analysis_processor = processor
    with Session(wallet.engine) as db:
        for name, account in [("own", "acct_i"), ("other", "acct_x")]:
            db.add(
                WalletInputRow(
                    input_id="inp_" + name,
                    account_id=account,
                    kind="TEXT",
                    original=b"synthetic",
                    accepted_at=stamp - 200,
                    expires_at=stamp + 3600,
                )
            )
            db.add(
                WalletAnalysisRow(
                    analysis_id="ana_" + name,
                    account_id=account,
                    input_id="inp_" + name,
                    request_id="req_" + name,
                    input_hash="0" * 64,
                    status="RUNNING",
                    accepted_at=stamp - 200,
                    started_at=stamp - 200,
                    retain_report=False,
                    retain_original=False,
                )
            )
        db.add(
            AuditEventRow(
                event_id="evt_background",
                actor_account_id="acct_i",
                action="wallet_analysis",
                target_id="ana_background",
                after_status="FAILED",
                created_at=datetime.fromtimestamp(stamp, UTC) - timedelta(days=31),
            )
        )
        db.commit()
    source = await input_ref(wallet)
    accepted = await wallet.client.post(
        "/v3/analyses", json={"request_id": "req_after_timeout", "input_ref": source}
    )
    assert accepted.status_code == 202, accepted.text
    await settle(wallet)
    with Session(wallet.engine) as db:
        assert db.get(WalletAnalysisRow, "ana_own").status == "FAILED"
        assert db.get(WalletAnalysisRow, "ana_other").status == "RUNNING"
        assert db.get(WalletInputRow, "inp_other").original == b"synthetic"
        assert db.get(AuditEventRow, "evt_background") is not None
    await module.cleanup(wallet.app)
    with Session(wallet.engine) as db:
        assert db.get(WalletAnalysisRow, "ana_other").status == "FAILED"
        assert db.get(WalletInputRow, "inp_other").original is None
        assert db.get(AuditEventRow, "evt_background") is None


@pytest.mark.parametrize(
    "retain_report,retain_original", [(False, False), (True, False), (False, True), (True, True)]
)
async def test_four_retention_choices_are_independent(wallet, retain_report, retain_original):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = processor
    source = await input_ref(w)
    body = {
        "request_id": "req_analysis",
        "input_ref": source,
        "retain_report": retain_report,
        "retain_original": retain_original,
    }
    accepted = await w.client.post("/v3/analyses", json=body)
    assert accepted.status_code == 202, accepted.text
    aid = accepted.json()["analysis_id"]
    await settle(w)
    result = await w.client.get(f"/v3/analyses/{aid}")
    assert result.json()["status"] == "COMPLETED", result.text
    assert result.json()["report"]["evidence"][0]["end_offset"] == 3
    assert result.json()["report"]["verification"] is None
    original = await w.client.get(f"/v3/analyses/{aid}/original")
    assert original.status_code == (200 if retain_original else 410)
    with Session(w.engine) as db:
        row = db.get(WalletAnalysisRow, aid)
        raw = db.get(WalletInputRow, source)
        assert (raw.original is not None) == retain_original
        assert row.report_expires_at - row.completed_at == (7 * 86400 if retain_report else 600)
        if retain_original:
            assert raw.expires_at - raw.accepted_at == 7 * 86400
    listed = await w.client.get("/v3/analyses")
    assert bool(listed.json()["items"]) == (retain_report or retain_original)
    assert (await w.client.post("/v3/analyses", json=body)).json()["analysis_id"] == aid
    assert (
        await w.client.post("/v3/analyses", json={**body, "retain_report": not retain_report})
    ).status_code == 409


async def test_unselected_input_and_other_owners_are_rejected(wallet):
    w = wallet
    assert (
        await w.client.post("/v3/inputs", json={"kind": "TEXT", "text": "합성 자료"})
    ).status_code == 409
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = processor
    source = await input_ref(w)
    w.who["name"] = "other"
    assert (
        await w.client.post("/v3/analyses", json={"request_id": "req_other", "input_ref": source})
    ).status_code == 404
    w.who["name"] = "issuer"
    accepted = await w.client.post(
        "/v3/analyses", json={"request_id": "req_owner", "input_ref": source}
    )
    aid = accepted.json()["analysis_id"]
    await settle(w)
    w.who["name"] = "other"
    for suffix in ("", "/report", "/original"):
        assert (await w.client.get(f"/v3/analyses/{aid}{suffix}")).status_code == 404
    assert (await w.client.delete(f"/v3/analyses/{aid}")).status_code == 404


@pytest.mark.parametrize("failure", ["grounding", "schema", "unavailable"])
async def test_provider_errors_do_not_leak_input_or_raw_responses(wallet, failure):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True

    async def bad(text):
        if failure == "unavailable":
            raise RuntimeError("DO_NOT_ECHO_" + text)
        value = report(text)
        if failure == "grounding":
            value["evidence"][0]["quote"] = "없는 인용문"
        else:
            value["risk_level"] = "MADE_UP"
        return value

    w.app.state.analysis_processor = bad
    source = await input_ref(w)
    accepted = await w.client.post(
        "/v3/analyses", json={"request_id": "req_bad", "input_ref": source}
    )
    await settle(w)
    result = await w.client.get(f"/v3/analyses/{accepted.json()['analysis_id']}")
    expected = {
        "grounding": "GROUNDING_MISMATCH",
        "schema": "ANALYZER_SCHEMA_MISMATCH",
        "unavailable": "ANALYZER_UNAVAILABLE",
    }[failure]
    assert result.json()["status"] == "FAILED" and result.json()["error_code"] == expected
    assert "DO_NOT_ECHO" not in result.text and "💡" not in result.text
    with Session(w.engine) as db:
        assert db.get(WalletInputRow, source).original is None


async def test_delete_running_job_fences_late_result(wallet):
    w = wallet
    started, release = asyncio.Event(), asyncio.Event()
    w.app.state.settings.wallet_text_input_enabled = True

    async def delayed(text):
        started.set()
        await release.wait()
        return report(text)

    w.app.state.analysis_processor = delayed
    source = await input_ref(w)
    accepted = await w.client.post(
        "/v3/analyses",
        json={
            "request_id": "req_late",
            "input_ref": source,
            "retain_report": True,
            "retain_original": True,
        },
    )
    aid = accepted.json()["analysis_id"]
    await asyncio.wait_for(started.wait(), timeout=2)
    assert (await w.client.delete(f"/v3/analyses/{aid}")).status_code == 204
    release.set()
    await settle(w)
    result = await w.client.get(f"/v3/analyses/{aid}")
    assert result.json()["status"] == "CANCELLED" and result.json()["report"] is None
    assert (await w.client.get(f"/v3/analyses/{aid}/original")).status_code == 410


async def test_account_parallel_and_window_limits_prevent_duplicate_work(wallet):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(text):
        started.set()
        await release.wait()
        return report(text)

    w.app.state.analysis_processor = delayed
    source = await input_ref(w)
    body = {"request_id": "req_first", "input_ref": source}
    first = await w.client.post("/v3/analyses", json=body)
    await asyncio.wait_for(started.wait(), timeout=2)
    same = await w.client.post("/v3/analyses", json=body)
    assert same.json()["analysis_id"] == first.json()["analysis_id"]
    second = await input_ref(w)
    assert (
        await w.client.post("/v3/analyses", json={"request_id": "req_busy", "input_ref": second})
    ).status_code == 429
    release.set()
    await settle(w)
    w.app.state.analysis_processor = processor
    for i in range(4):
        value = await input_ref(w)
        response = await w.client.post(
            "/v3/analyses", json={"request_id": f"req_next_{i}", "input_ref": value}
        )
        assert response.status_code == 202, response.text
        await settle(w)
    value = await input_ref(w)
    assert (
        await w.client.post("/v3/analyses", json={"request_id": "req_sixth", "input_ref": value})
    ).status_code == 429


async def test_exempt_test_account_skips_window_limit_but_not_parallel_guard(wallet):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.settings.analysis_limit_exempt_usernames = ["i"]
    for i in range(7):
        value = await input_ref(w)
        response = await w.client.post(
            "/v3/analyses", json={"request_id": f"req_exempt_{i}", "input_ref": value}
        )
        assert response.status_code == 202, response.text
        await settle(w)
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(text):
        started.set()
        await release.wait()
        return report(text)

    w.app.state.analysis_processor = delayed
    slow = await input_ref(w)
    await w.client.post("/v3/analyses", json={"request_id": "req_slow", "input_ref": slow})
    await asyncio.wait_for(started.wait(), timeout=2)
    busy = await w.client.post(
        "/v3/analyses", json={"request_id": "req_busy", "input_ref": await input_ref(w)}
    )
    assert busy.status_code == 429
    release.set()
    await settle(w)
    w.app.state.analysis_processor = processor
    w.who["name"] = "recipient"
    for i in range(5):
        value = await input_ref(w)
        await w.client.post("/v3/analyses", json={"request_id": f"req_r_{i}", "input_ref": value})
        await settle(w)
    blocked = await w.client.post(
        "/v3/analyses", json={"request_id": "req_r_6", "input_ref": await input_ref(w)}
    )
    assert blocked.status_code == 429


async def test_restart_timeout_and_late_completion_keep_failure(wallet, monkeypatch):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True
    clock = [int(time.time())]
    monkeypatch.setattr(module, "now", lambda: clock[0])
    source = await input_ref(w)
    with Session(w.engine) as db:
        db.add(
            WalletAnalysisRow(
                analysis_id="ana_restart",
                account_id="acct_i",
                input_id=source,
                request_id="req_restart",
                input_hash="0" * 64,
                status="RUNNING",
                accepted_at=clock[0],
                started_at=clock[0],
                retain_report=False,
                retain_original=False,
            )
        )
        db.commit()
    await module.cleanup(w.app, restart=True)
    with Session(w.engine) as db:
        assert db.get(WalletAnalysisRow, "ana_restart").error_code == "PROCESS_RESTARTED"
        assert db.get(WalletInputRow, source).original is None
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(text):
        started.set()
        await release.wait()
        return report(text)

    w.app.state.analysis_processor = delayed
    source2 = await input_ref(w)
    accepted = await w.client.post(
        "/v3/analyses", json={"request_id": "req_timeout", "input_ref": source2}
    )
    aid = accepted.json()["analysis_id"]
    await asyncio.wait_for(started.wait(), timeout=2)
    clock[0] += 180
    await module.cleanup(w.app)
    release.set()
    await settle(w)
    value = (await w.client.get(f"/v3/analyses/{aid}")).json()
    assert value["status"] == "FAILED" and value["error_code"] == "ANALYSIS_TIMEOUT"


@pytest.mark.parametrize("risk,tampered", [("HIGH", False), ("NO_CLEAR_INDICATORS", True)])
async def test_issuance_result_is_attached_by_c_and_independent_of_risk(wallet, risk, tampered):
    w = wallet
    await activated(w)
    signing = await draft(w)
    doc, _ = await confirmed_publication(w, signing)
    fields = signing["content"] | ({"amount_minor": 154001} if tampered else {})
    verified = await w.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_for_report",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": fields,
        },
    )
    sid = verified.json()["session_id"]
    w.app.state.settings.wallet_text_input_enabled = True

    async def analyst(text):
        return report(text, risk)

    w.app.state.analysis_processor = analyst
    source = await input_ref(w)
    response = await w.client.post(
        "/v3/analyses",
        json={"request_id": "req_merged", "input_ref": source, "verification_session_id": sid},
    )
    assert response.status_code == 202, response.text
    await settle(w)
    result = (await w.client.get(f"/v3/analyses/{response.json()['analysis_id']}/report")).json()
    assert result["risk_level"] == risk
    assert result["verification"]["verification_status"] == ("TAMPERED" if tampered else "VERIFIED")
    w.who["name"] = "other"
    other_input = await input_ref(w)
    denied = await w.client.post(
        "/v3/analyses",
        json={
            "request_id": "req_stolen_session",
            "input_ref": other_input,
            "verification_session_id": sid,
        },
    )
    assert denied.status_code == 404


async def test_analyzer_cannot_supply_issuance_authority(wallet):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True

    async def forged(text):
        value = report(text)
        value["verification_not_run_reason"] = None
        value["verification"] = {
            "session_id": "vsn_forged",
            "verification_status": "INCONCLUSIVE",
            "comparison_scope": "ID_ONLY",
            "checks": [],
            "reason_codes": [],
            "checked_at": 1,
            "chain_id": "31337",
            "verifying_contract": "0x" + "12" * 20,
        }
        return value

    w.app.state.analysis_processor = forged
    source = await input_ref(w)
    accepted = await w.client.post(
        "/v3/analyses", json={"request_id": "req_authority", "input_ref": source}
    )
    await settle(w)
    result = (await w.client.get(f"/v3/analyses/{accepted.json()['analysis_id']}")).json()
    assert result["error_code"] == "ANALYZER_AUTHORITY_VIOLATION"


async def test_expiry_blocks_access_before_physical_cleanup_and_preserves_institution_original(
    wallet, monkeypatch
):
    from originproof_api import wallet_documents
    from originproof_api.wallet_database import WalletDocumentRow, WalletSigningRow
    from test_wallet_runtime import DOMAIN

    w = wallet
    await activated(w)
    signing = await draft(w)
    doc, _ = await confirmed_publication(w, signing)
    clock = [int(time.time())]
    monkeypatch.setattr(module, "now", lambda: clock[0])
    monkeypatch.setattr(wallet_documents, "now", lambda: clock[0])
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = processor
    source = await input_ref(w)
    accepted = await w.client.post(
        "/v3/analyses",
        json={
            "request_id": "req_expiry",
            "input_ref": source,
            "retain_report": False,
            "retain_original": True,
        },
    )
    aid = accepted.json()["analysis_id"]
    await settle(w)
    with Session(w.engine) as db:
        row = db.get(WalletAnalysisRow, aid)
        clock[0] = row.report_expires_at
    assert (await w.client.get(f"/v3/analyses/{aid}/report")).status_code == 410
    assert (await w.client.get(f"/v3/analyses/{aid}/original")).status_code == 200
    with Session(w.engine) as db:
        clock[0] = db.get(WalletInputRow, source).expires_at
    assert (await w.client.get(f"/v3/analyses/{aid}/original")).status_code == 410
    await module.cleanup(w.app)
    identity = ("31337", DOMAIN.verifying_contract, doc.document_id, 1)
    with Session(w.engine) as db:
        assert db.get(WalletInputRow, source).original is None
        institution = db.get(WalletDocumentRow, identity)
        assert institution.original is not None
        clock[0] = institution.retain_until
    await module.cleanup(w.app)
    with Session(w.engine) as db:
        institution = db.get(WalletDocumentRow, identity)
        source = db.get(WalletSigningRow, signing["signing_request_id"])
        assert institution.original is None and institution.content == {}
        assert source.payload["original_base64"] is None and source.payload["content"] is None
    assert (
        await w.client.get(f"/v3/documents/{doc.document_id}/verification-material")
    ).status_code == 410


@pytest.mark.parametrize("code", ["REFUSAL", "TIMEOUT", "RATE_LIMIT", "INCOMPLETE_OUTPUT"])
async def test_known_analyzer_failure_codes_survive_without_provider_details(wallet, code):
    class Failure(Exception):
        pass

    async def rejected(text):
        problem = Failure("DO_NOT_ECHO_" + text)
        problem.code = code
        raise problem

    wallet.app.state.settings.wallet_text_input_enabled = True
    wallet.app.state.analysis_processor = rejected
    source = await input_ref(wallet)
    accepted = await wallet.client.post(
        "/v3/analyses", json={"request_id": "req_provider_failure", "input_ref": source}
    )
    await settle(wallet)
    result = await wallet.client.get(f"/v3/analyses/{accepted.json()['analysis_id']}")
    assert result.json()["status"] == "FAILED" and result.json()["error_code"] == code
    assert "DO_NOT_ECHO" not in result.text and result.json()["report"] is None
