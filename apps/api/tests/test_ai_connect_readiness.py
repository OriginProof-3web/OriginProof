"""Injected Mock HTTP baseline; no production wiring or paid provider calls."""

import asyncio
import base64
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from originproof_analyzer.converted_inputs import ConvertedText
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider
from originproof_api.main import app, create_app, openai_document_converter

pytest_plugins = ("test_wallet_runtime",)


def test_production_app_wires_phishing_analyzer():
    assert isinstance(app.state.analysis_processor, PhishingAnalyzer)
    assert create_app().state.analysis_processor is None  # tests and fixtures inject explicitly


@pytest.mark.parametrize(
    "boundary,fault",
    [("none", None), ("provider", "quote"), ("api", "quote"), ("api", "offset")],
)
async def test_mock_processor_http_grounding(wallet, boundary, fault):
    text = "💡 합성 안내: 별도 창구 확인"
    quote = "별도 창구 확인"
    start = text.index(quote)
    evidence = {
        "rule_id": "SYNTHETIC_CONTEXT",
        "quote": "없는 인용" if boundary == "provider" else quote,
        "start_offset": start,
        "end_offset": start + len(quote),
        "source": "LLM",
    }
    provider = MockLLMProvider(
        analysis_replays={
            hashlib.sha256(text.encode()).hexdigest(): {
                "risk_level": "CAUTION",
                "evidence": [evidence],
                "limitations": ["SYNTHETIC_REPLAY"],
                "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
            }
        }
    )
    analyzer = PhishingAnalyzer(provider)

    async def processor(value):
        result = await analyzer(value)
        if boundary == "api":
            # Fault injection AFTER D validation proves C independently checks grounding.
            item = result.evidence[0]
            change = {"quote": "없는 인용"} if fault == "quote" else {"start_offset": start + 1}
            result = result.model_copy(update={"evidence": [item.model_copy(update=change)]})
        return result

    app = create_app(
        database=wallet.app.state.database,
        settings=wallet.app.state.settings.model_copy(update={"wallet_text_input_enabled": True}),
        analysis_processor=analyzer if boundary != "api" else processor,
    )
    # Existing synthetic account/CSRF fixture; authentication itself is outside this baseline.
    app.dependency_overrides.update(wallet.app.dependency_overrides)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-CSRF-Token": "csrf"},
    ) as client:
        try:
            uploaded = await client.post("/v3/inputs", json={"kind": "TEXT", "text": text})
            assert uploaded.status_code == 201, uploaded.text
            accepted = await client.post(
                "/v3/analyses",
                json={"request_id": "req_mock_connect", "input_ref": uploaded.json()["input_ref"]},
            )
            assert accepted.status_code == 202, accepted.text
            assert accepted.json()["status"] == "QUEUED"
            await asyncio.wait_for(asyncio.gather(*list(app.state.analysis_tasks)), timeout=10)
            assert app.state.analysis_worker_error is None
            response = await client.get(f"/v3/analyses/{accepted.json()['analysis_id']}")
            assert response.status_code == 200, response.text
            job = response.json()
            if boundary == "api":
                assert job["status"] == "FAILED"
                assert job["error_code"] == "GROUNDING_MISMATCH"
                assert job["report"] is None
            else:
                assert job["status"] == "COMPLETED"
                assert job["error_code"] is None
                report = job["report"]
                assert report["verification"] is None
                assert report["verification_not_run_reason"] == "NO_DOCUMENT_REFERENCE"
                if boundary == "provider":
                    assert report["risk_level"] == "UNDETERMINED"
                    assert report["evidence"] == []
                    assert "LLM_ANALYSIS_UNAVAILABLE:GROUNDING_MISMATCH" in report["limitations"]
                else:
                    assert report["risk_level"] == "CAUTION"
                    assert "MOCK_REPLAY_NOT_MODEL_PERFORMANCE" in report["limitations"]
                    item = report["evidence"][0]
                    assert item["source"] == "LLM"
                    assert (item["start_offset"], item["end_offset"]) == (start, start + len(quote))
                    assert text[item["start_offset"] : item["end_offset"]] == item["quote"] == quote
        finally:
            pending = list(app.state.analysis_tasks)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

ROOT = Path(__file__).resolve().parents[3]
MEDIA = ROOT / "fixtures/synthetic/media_safety_v1"


def image_body(name):
    data = base64.b64encode((MEDIA / name).read_bytes()).decode()
    return {"kind": "DOCUMENT_IMAGE", "image_media_type": "image/png", "image_base64": data}


@pytest.mark.parametrize("case", ["disabled", "spoofed", "no_converter", "converted", "too_large"])
async def test_document_image_input(wallet, case):
    text = "합성 안내: 별도 창구 확인"
    quote = "별도 창구 확인"
    analyzer = PhishingAnalyzer(
        MockLLMProvider(
            analysis_replays={
                hashlib.sha256(text.encode()).hexdigest(): {
                    "risk_level": "CAUTION",
                    "evidence": [
                        {
                            "rule_id": "SYNTHETIC_CONTEXT",
                            "quote": quote,
                            "start_offset": text.index(quote),
                            "end_offset": text.index(quote) + len(quote),
                            "source": "LLM",
                        }
                    ],
                    "limitations": [],
                    "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
                }
            }
        )
    )
    seen = []

    async def converter(artifact, remaining):
        seen.append((artifact.kind, artifact.image_media_type))
        return ConvertedText(
            kind="DOCUMENT_IMAGE", complete=True, segments=[{"text": text, "page": 1}]
        )

    update = {"wallet_text_input_enabled": True, "wallet_image_input_enabled": case != "disabled"}
    if case in ("too_large", "converted"):
        # The ~12KB photo exceeds this cap: only the enabled image route may lift it.
        update |= {
            "wallet_image_input_enabled": case == "converted",
            "request_body_max_bytes": 1024,
        }
    app = create_app(
        database=wallet.app.state.database,
        settings=wallet.app.state.settings.model_copy(update=update),
        analysis_processor=analyzer,
        image_converter=None if case == "no_converter" else converter,
    )
    app.dependency_overrides.update(wallet.app.dependency_overrides)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-CSRF-Token": "csrf"}
    ) as client:
        try:
            body = image_body("spoofed.png" if case == "spoofed" else "clear.png")
            uploaded = await client.post("/v3/inputs", json=body)
            expected = {"disabled": 409, "spoofed": 422, "too_large": 413}.get(case, 201)
            assert uploaded.status_code == expected, uploaded.text
            if expected != 201:
                return
            accepted = await client.post(
                "/v3/analyses",
                json={
                    "request_id": "req_image_" + case,
                    "input_ref": uploaded.json()["input_ref"],
                    "retain_original": case == "converted",
                },
            )
            assert accepted.status_code == 202, accepted.text
            await asyncio.wait_for(asyncio.gather(*list(app.state.analysis_tasks)), timeout=10)
            job = (await client.get(f"/v3/analyses/{accepted.json()['analysis_id']}")).json()
            if case == "no_converter":
                assert (job["status"], job["error_code"]) == ("FAILED", "ANALYZER_UNAVAILABLE")
                return
            assert job["status"] == "COMPLETED", job
            assert seen == [("image", "image/png")]
            report = job["report"]
            assert "CONVERSION_ACCURACY_NOT_VERIFIED" in report["limitations"]
            item = next(e for e in report["evidence"] if e["source"] == "LLM")
            assert text[item["start_offset"] : item["end_offset"]] == item["quote"] == quote
            original = await client.get(f"/v3/analyses/{accepted.json()['analysis_id']}/original")
            assert original.status_code == 200, original.text
            assert original.headers["content-type"] == "image/png"
            assert original.headers["content-disposition"].endswith('.png"')
            assert original.content == (MEDIA / "clear.png").read_bytes()
        finally:
            pending = list(app.state.analysis_tasks)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)


async def test_production_image_converter_fails_closed_without_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    with pytest.raises(AnalyzerError) as raised:
        await openai_document_converter(None, 10)
    assert raised.value.code == AnalyzerErrorCode.PROVIDER_UNAVAILABLE


@pytest.mark.parametrize("enabled", [False, True])
async def test_image_only_lifespan_cleans_expired_originals_and_runs_maintenance(
    wallet, monkeypatch, enabled
):
    import originproof_api.main as composition
    from originproof_api.wallet_database import WalletInputRow
    from sqlalchemy.orm import Session

    database = wallet.app.state.database
    monkeypatch.setattr(database, "dispose", AsyncMock(), raising=False)
    started = asyncio.Event()

    async def background(app, stop):
        started.set()
        await stop.wait()

    monkeypatch.setattr(composition, "maintenance", background)
    settings = wallet.app.state.settings.model_copy(
        update={
            "wallet_registry_address": None,
            "wallet_text_input_enabled": False,
            "wallet_demo_email_enabled": False,
            "wallet_image_input_enabled": enabled,
        }
    )
    with Session(wallet.engine) as db:
        db.add(WalletInputRow(
            input_id="inp_expired_photo", account_id="acct_i", kind="DOCUMENT_IMAGE",
            original=b"synthetic expired original", accepted_at=0, expires_at=1,
        ))
        db.commit()
    app = create_app(database=database, settings=settings)
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)
        assert started.is_set() is enabled
        with Session(wallet.engine) as db:
            original = db.get(WalletInputRow, "inp_expired_photo").original
            assert (original is None) is enabled
