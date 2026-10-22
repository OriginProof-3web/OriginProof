"""D callback against the same-head C API: ASGI/SQLite, synthetic Registry and LLM."""

import asyncio
import hashlib
import socket

import pytest
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider
from originproof_api.wallet_database import WalletAnalysisRow, WalletInputRow
from sqlalchemy.orm import Session
from test_wallet_analyses import input_ref, settle
from test_wallet_runtime import activated, confirmed_publication, draft

pytest_plugins = ("test_wallet_runtime",)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    def forbidden(*args, **kwargs):
        raise AssertionError("This QA permits only ASGI transport and in-memory SQLite")

    monkeypatch.setattr(socket.socket, "connect", forbidden)


def replay(text, risk="NO_CLEAR_INDICATORS", evidence=None):
    value = {
        "risk_level": risk,
        "evidence": evidence or [],
        "limitations": ["D synthetic LLM replay"],
        "verification": None,
        "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
    }
    return MockLLMProvider(analysis_replays={hashlib.sha256(text.encode()).hexdigest(): value})


async def analyze(w, text, *, sid=None, **choices):
    ref = await input_ref(w, text)
    body = {"request_id": "req_d_analysis", "input_ref": ref, **choices}
    if sid is not None:
        body["verification_session_id"] = sid
    response = await w.client.post("/v3/analyses", json=body)
    assert response.status_code == 202, response.text
    await settle(w)
    aid = response.json()["analysis_id"]
    result = await w.client.get(f"/v3/analyses/{aid}")
    assert result.status_code == 200 and result.json()["status"] == "COMPLETED", result.text
    return aid, ref, result.json()["report"]


async def test_input_stays_unselected_by_default(wallet):
    assert not wallet.app.state.settings.wallet_text_input_enabled
    response = await wallet.client.post("/v3/inputs", json={"kind": "TEXT", "text": "합성 자료"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "retain_report,retain_original", [(False, False), (True, False), (False, True), (True, True)]
)
async def test_actual_d_callback_retention(wallet, retain_report, retain_original):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True  # This isolated test app only.
    w.app.state.analysis_processor = PhishingAnalyzer(MockLLMProvider())
    text = "🧪 인증번호를 알려주세요"
    aid, ref, report = await analyze(
        w, text, retain_report=retain_report, retain_original=retain_original
    )
    assert report["risk_level"] == "HIGH" and report["verification"] is None
    assert any(x.startswith("LLM_ANALYSIS_UNAVAILABLE:") for x in report["limitations"])
    for evidence in report["evidence"]:
        assert evidence["source"] == "RULE"
        assert text[evidence["start_offset"] : evidence["end_offset"]] == evidence["quote"]
    assert (await w.client.get(f"/v3/analyses/{aid}/original")).status_code == (
        200 if retain_original else 410
    )
    with Session(w.engine) as db:
        row, raw = db.get(WalletAnalysisRow, aid), db.get(WalletInputRow, ref)
        assert row.report_expires_at - row.completed_at == (604800 if retain_report else 600)
        assert (raw.original is not None) == retain_original
        if retain_original:
            assert raw.expires_at - raw.accepted_at == 604800
    listed = await w.client.get("/v3/analyses")
    assert bool(listed.json()["items"]) == (retain_report or retain_original)


@pytest.mark.parametrize("tampered", [False, True])
async def test_risk_and_issuance_are_independent(wallet, tampered):
    w = wallet
    await activated(w)
    signing = await draft(w)
    doc, _ = await confirmed_publication(w, signing)
    verified = await w.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_d_verification",
            "document_id": doc.document_id,
            "scope": "PROTECTED_FIELDS",
            "candidate": signing["content"] | ({"amount_minor": 154001} if tampered else {}),
        },
    )
    assert verified.status_code == 200, verified.text
    snapshot = verified.json()
    text = "예약된 일정은 합성 안내 창구에서 확인합니다" if tampered else "인증번호를 알려주세요"
    provider = replay(text) if tampered else MockLLMProvider()
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = PhishingAnalyzer(provider)
    _, _, report = await analyze(w, text, sid=snapshot["session_id"])
    assert report["risk_level"] == ("NO_CLEAR_INDICATORS" if tampered else "HIGH")
    assert report["verification"] == snapshot
    assert snapshot["verification_status"] == ("TAMPERED" if tampered else "VERIFIED")
    assert snapshot["comparison_scope"] == "FULL_COMPARISON"
    assert report["verification_not_run_reason"] is None
    w.who["name"] = "other"
    ref = await input_ref(w, "다른 계정의 합성 입력")
    denied = await w.client.post(
        "/v3/analyses",
        json={
            "request_id": "req_stolen_session",
            "input_ref": ref,
            "verification_session_id": snapshot["session_id"],
        },
    )
    assert denied.status_code == 404


@pytest.mark.parametrize("unavailable", [False, True])
async def test_not_registered_or_rpc_unavailable_does_not_clear_risk(
    wallet, unavailable, monkeypatch
):
    w = wallet
    if unavailable:

        async def lost_rpc(*args):
            raise TimeoutError("synthetic RPC outage")

        monkeypatch.setattr(w.chain, "document", lost_rpc)
    verification = await w.client.post(
        "/v3/verifications",
        json={
            "request_id": "req_unknown",
            "document_id": "0x" + "fe" * 32,
            "scope": "ID_ONLY",
        },
    )
    assert verification.status_code == 200, verification.text
    snapshot = verification.json()
    assert snapshot["verification_status"] == ("INCONCLUSIVE" if unavailable else "NOT_REGISTERED")
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = PhishingAnalyzer(MockLLMProvider())
    _, _, report = await analyze(w, "인증번호를 알려주세요", sid=snapshot["session_id"])
    assert report["risk_level"] == "HIGH"
    assert report["verification"] == snapshot


async def test_overlapping_model_quote_is_quarantined_before_c_storage(wallet):
    w = wallet
    text = "하하하"
    provider = replay(
        text,
        "CAUTION",
        [
            {
                "rule_id": "DG12",
                "quote": "하하",
                "source": "LLM",
                "start_offset": None,
                "end_offset": None,
            }
        ],
    )
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = PhishingAnalyzer(provider)
    _, _, report = await analyze(w, text)
    assert report["risk_level"] == "UNDETERMINED" and report["evidence"] == []
    assert "LLM_ANALYSIS_UNAVAILABLE:GROUNDING_MISMATCH" in report["limitations"]


async def test_actual_d_late_completion_cannot_restore_deleted_original(wallet):
    w = wallet
    started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()

    class DelayedProvider(MockLLMProvider):
        async def analyze_phishing(self, text):
            started.set()
            await release.wait()
            value = await replay(text).analyze_phishing(text)
            finished.set()
            return value

    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = PhishingAnalyzer(DelayedProvider())
    ref = await input_ref(w, "예약 일정 합성 안내")
    accepted = await w.client.post(
        "/v3/analyses",
        json={
            "request_id": "req_cancel",
            "input_ref": ref,
            "retain_report": True,
            "retain_original": True,
        },
    )
    assert accepted.status_code == 202, accepted.text
    aid = accepted.json()["analysis_id"]
    await asyncio.wait_for(started.wait(), timeout=2)
    assert (await w.client.delete(f"/v3/analyses/{aid}")).status_code == 204
    release.set()
    await settle(w)
    assert finished.is_set()  # C uses a durable deletion fence, not task cancellation.
    result = (await w.client.get(f"/v3/analyses/{aid}")).json()
    assert result["status"] == "CANCELLED" and result["report"] is None
    assert (await w.client.get(f"/v3/analyses/{aid}/original")).status_code == 410
    with Session(w.engine) as db:
        assert db.get(WalletInputRow, ref).original is None


async def test_actual_d_report_is_owner_only(wallet):
    w = wallet
    w.app.state.settings.wallet_text_input_enabled = True
    w.app.state.analysis_processor = PhishingAnalyzer(MockLLMProvider())
    aid, _, _ = await analyze(w, "인증번호를 알려주세요", retain_report=True, retain_original=True)
    w.who["name"] = "other"
    for suffix in ("", "/report", "/original"):
        assert (await w.client.get(f"/v3/analyses/{aid}{suffix}")).status_code == 404
    assert (await w.client.delete(f"/v3/analyses/{aid}")).status_code == 404
