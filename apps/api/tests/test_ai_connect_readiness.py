"""Injected Mock HTTP baseline; no production wiring or paid provider calls."""

import asyncio
import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider
from originproof_api.main import create_app

pytest_plugins = ("test_wallet_runtime",)


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
