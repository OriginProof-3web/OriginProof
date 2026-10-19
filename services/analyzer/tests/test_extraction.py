import base64
import hashlib
import json
import logging
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from originproof_analyzer.errors import HTTP_STATUS, AnalyzerError, AnalyzerErrorCode
from originproof_analyzer.inputs import MAX_IMAGE_BYTES, SemanticInput
from originproof_analyzer.main import create_app
from originproof_analyzer.providers import MockLLMProvider
from originproof_analyzer.service import SemanticInterface
from originproof_analyzer.settings import AnalyzerSettings
from originproof_analyzer.validation import EXTRACTED_FIELDS
from originproof_core import CardPaymentNoticeCandidate
from PIL import Image, ImageDraw
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "fixtures" / "mvp"
CASES = json.loads((FIXTURES / "analyzer_cases.json").read_text())["cases"]


def image_bytes(text="SYNTHETIC FIXTURE", *, format="PNG", size=(860, 500)) -> bytes:
    buffer = BytesIO()
    picture = Image.new("RGB", size, "white")
    ImageDraw.Draw(picture).multiline_text((24, 24), text, fill="black", spacing=12, font_size=22)
    picture.save(buffer, format=format)
    return buffer.getvalue()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_text_cases(case):
    assert case["source"] == "synthetic"
    service = SemanticInterface(MockLLMProvider())
    if "expected_error" in case:
        with pytest.raises(AnalyzerError) as caught:
            service.analyze_card_payment_notice(SemanticInput(text=case["text"]))
        assert caught.value.code == case["expected_error"]
    else:
        candidate = service.analyze_card_payment_notice(SemanticInput(text=case["text"]))
        assert type(candidate) is CardPaymentNoticeCandidate
        assert candidate.model_dump(mode="json") == case["expected"]
        assert set(candidate.model_dump()) == set(CardPaymentNoticeCandidate.model_fields)
        if "golden" in case:
            golden = json.loads((FIXTURES / case["golden"]).read_text())
            assert {name: case["expected"][name] for name in EXTRACTED_FIELDS} == {
                name: golden[name] for name in EXTRACTED_FIELDS
            }


def test_existing_golden_fixtures_differ_only_in_amount():
    valid = json.loads((FIXTURES / "card_notice_valid.json").read_text())
    changed = json.loads((FIXTURES / "card_notice_amount_tampered.json").read_text())
    assert [name for name in EXTRACTED_FIELDS if valid[name] != changed[name]] == ["amount_minor"]


@pytest.mark.parametrize("case", CASES[:2], ids=lambda case: case["id"])
def test_synthetic_image_replay_matches_text_candidate(case):
    data = image_bytes(case["text"])
    provider = MockLLMProvider(image_replays={hashlib.sha256(data).hexdigest(): case["text"]})
    artifact = SemanticInput(
        image_base64=base64.b64encode(data).decode(), image_media_type="image/png"
    )
    service = SemanticInterface(provider)
    assert service.analyze_card_payment_notice(artifact).model_dump(mode="json") == case["expected"]
    assert service.analyze_card_payment_notice(artifact) == service.analyze_card_payment_notice(
        SemanticInput(text=case["text"])
    )
    with TestClient(create_app(service)) as client:
        assert (
            client.post("/v1/analyze/card-payment-notice", json=artifact.model_dump()).json()
            == case["expected"]
        )


def test_mock_never_uses_unknown_image_or_image_filename():
    artifact = SemanticInput(
        image_base64=base64.b64encode(image_bytes()).decode(),
        image_media_type="image/png",
    )
    with pytest.raises(AnalyzerError, match="not supported"):
        SemanticInterface(MockLLMProvider()).analyze_card_payment_notice(artifact)


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"text": "  "},
        {"text": "x" * 10001},
        {"text": "PRIVATE", "image_base64": "PRIVATE"},
        {"text": "PRIVATE", "image_media_type": "image/png"},
        {"image_base64": "PRIVATE", "image_media_type": "image/png"},
        {"image_base64": "c3ludGhldGlj", "image_media_type": "image/png"},
        {"text": "PRIVATE", "verification_status": "VERIFIED"},
    ],
)
def test_invalid_input_is_redacted(data):
    with TestClient(create_app(settings=AnalyzerSettings(llm_provider="mock"))) as client:
        response = client.post("/v1/analyze/card-payment-notice", json=data)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MALFORMED_INPUT"
    assert "PRIVATE" not in response.text


@pytest.mark.parametrize("kind", ["damaged", "mime", "bytes", "pixels", "frames"])
def test_image_limits(kind):
    data = image_bytes()
    mime = "image/png"
    if kind == "damaged":
        data = data[:40]
    elif kind == "mime":
        mime = "image/jpeg"
    elif kind == "bytes":
        data = b"\x89PNG\r\n\x1a\n" + b"x" * MAX_IMAGE_BYTES
    elif kind == "pixels":
        data = image_bytes(size=(4001, 3000))
    else:
        buffer = BytesIO()
        Image.new("RGB", (30, 30), "white").save(
            buffer,
            format="PNG",
            save_all=True,
            append_images=[Image.new("RGB", (30, 30), "black")],
        )
        data = buffer.getvalue()
    with pytest.raises(ValidationError):
        SemanticInput(image_base64=base64.b64encode(data).decode(), image_media_type=mime)


@pytest.mark.parametrize(
    "format,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_supported_image_formats(format, mime):
    assert (
        SemanticInput(
            image_base64=base64.b64encode(image_bytes(format=format)).decode(),
            image_media_type=mime,
        ).kind
        == "image"
    )


@pytest.mark.parametrize("code", list(AnalyzerErrorCode))
def test_mock_faults_have_safe_http_contract(code, normal_case):
    service = SemanticInterface(MockLLMProvider(error=code))
    with TestClient(create_app(service)) as client:
        response = client.post(
            "/v1/analyze/card-payment-notice", json={"text": normal_case["text"]}
        )
    assert response.status_code == HTTP_STATUS[code]
    assert response.json() == AnalyzerError(code).as_response()
    assert "verification_status" not in response.text


def test_api_uses_shared_schema_and_health_contract(normal_case):
    with TestClient(create_app()) as client:
        assert client.get("/health/live").json() == {"status": "live"}
        assert client.get("/v1/capabilities").json()["image_mode"] == "unsupported"
        response = client.post(
            "/v1/analyze/card-payment-notice", json={"text": normal_case["text"]}
        )
        assert response.json() == normal_case["expected"]
        schema = client.get("/openapi.json").json()["components"]["schemas"][
            "CardPaymentNoticeCandidate"
        ]
    shared = CardPaymentNoticeCandidate.model_json_schema()
    assert schema["properties"].keys() == shared["properties"].keys()
    assert schema["additionalProperties"] is False
    generated = json.loads(
        (
            ROOT / "packages/schemas/generated/json/card-payment-notice-candidate.schema.json"
        ).read_text()
    )
    generated.pop("$schema")
    assert generated == shared


@pytest.mark.parametrize(
    "before,after",
    [
        ("154,000 KRW", "154000"),
        ("154,000 KRW", "-1 KRW"),
        ("154,000 KRW", "0 KRW"),
        ("154,000 KRW", "1.5 KRW"),
        ("****1234", "1234567890123456"),
        ("2026-09-03 12:14 KST", "2026-02-30 12:14 KST"),
    ],
)
def test_invalid_visible_values_are_not_repaired(normal_case, before, after):
    with pytest.raises(AnalyzerError) as caught:
        SemanticInterface(MockLLMProvider()).analyze_card_payment_notice(
            SemanticInput(text=normal_case["text"].replace(before, after))
        )
    assert caught.value.code == AnalyzerErrorCode.SCHEMA_MISMATCH


def test_conflicting_amounts_are_not_selected_by_proof_id(normal_case):
    with pytest.raises(AnalyzerError) as caught:
        SemanticInterface(MockLLMProvider()).analyze_card_payment_notice(
            SemanticInput(text=normal_case["text"] + "\nAmount: 1 KRW")
        )
    assert caught.value.code == AnalyzerErrorCode.SCHEMA_MISMATCH


def test_metadata_does_not_record_input_or_candidate(caplog, normal_case):
    caplog.set_level(logging.INFO, logger="originproof_analyzer.service")
    SemanticInterface(MockLLMProvider()).analyze_card_payment_notice(
        SemanticInput(text=normal_case["text"])
    )
    metadata = next(record.analyzer for record in caplog.records if hasattr(record, "analyzer"))
    assert metadata["model"] == "deterministic-template-v3"
    assert metadata["prompt_version"] == "card_payment_notice_v4"
    assert metadata["input_kind"] == "text"
    assert metadata["duration_ms"] >= 0
    assert all(
        value not in json.dumps(metadata) for value in ["prf_demo_001", "ORIGIN CAFE", "154000"]
    )


def test_settings_from_environment_and_secret_redaction(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "medium")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    settings = AnalyzerSettings()
    assert (settings.llm_provider, settings.openai_model) == ("openai", "configured-model")
    assert (settings.llm_timeout_seconds, settings.llm_max_retries) == (3, 1)
    assert settings.openai_reasoning_effort == "medium"
    assert "synthetic-key-placeholder" not in repr(settings)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"llm_provider": "unknown"},
        {"llm_timeout_seconds": 0},
        {"llm_timeout_seconds": float("inf")},
        {"llm_max_retries": 3},
        {"analyzer_min_confidence": 1.1},
        {"openai_reasoning_effort": "unknown"},
    ],
)
def test_invalid_settings(kwargs):
    with pytest.raises(ValidationError):
        AnalyzerSettings(**kwargs)


def test_openai_without_key_keeps_health_but_does_not_fallback(normal_case):
    with TestClient(create_app(settings=AnalyzerSettings(llm_provider="openai"))) as client:
        assert client.get("/health/live").status_code == 200
        response = client.post(
            "/v1/analyze/card-payment-notice", json={"text": normal_case["text"]}
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
