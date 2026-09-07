"""The real OpenAI SDK over MockTransport: no API key, external request, or live inference."""

import base64
import json
from io import BytesIO

import httpx
import pytest
from openai import OpenAI
from originproof_analyzer.errors import AnalyzerError
from originproof_analyzer.inputs import SemanticInput
from originproof_analyzer.providers import OpenAILLMProvider
from originproof_analyzer.service import SemanticInterface
from originproof_analyzer.settings import AnalyzerSettings
from originproof_core import CardPaymentNoticeCandidate
from PIL import Image


def response_body(data, *, status="completed", refusal=False, empty=False):
    part = (
        {"type": "refusal", "refusal": "PRIVATE_REFUSAL"}
        if refusal
        else {
            "type": "output_text",
            "text": json.dumps(data),
            "annotations": [],
        }
    )
    return {
        "id": "resp_test_only",
        "object": "response",
        "created_at": 0,
        "status": status,
        "model": "configured-model",
        "error": None,
        "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
        "output": []
        if empty
        else [
            {
                "id": "msg_test",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [part],
            }
        ],
        "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
    }


@pytest.fixture
def make_provider():
    clients = []

    def factory(handler, *, max_retries=0):
        client = OpenAI(
            api_key="synthetic-test-placeholder",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        clients.append(client)
        return OpenAILLMProvider(
            AnalyzerSettings(
                openai_model="configured-model",
                llm_timeout_seconds=3,
                llm_max_retries=max_retries,
            ),
            client=client,
        )

    yield factory
    for client in clients:
        client.close()


@pytest.mark.parametrize("image_input", [False, True])
def test_sdk_roundtrip_uses_authoritative_shared_schema(make_provider, normal_case, image_input):
    observed = []

    def handler(request):
        observed.append((json.loads(request.content), request.extensions["timeout"]))
        return httpx.Response(200, json=response_body(normal_case["expected"]))

    artifact = SemanticInput(text=normal_case["text"])
    if image_input:
        buffer = BytesIO()
        Image.new("RGB", (40, 40), "white").save(buffer, format="PNG")
        artifact = SemanticInput(
            image_base64=base64.b64encode(buffer.getvalue()).decode(),
            image_media_type="image/png",
        )
    result = make_provider(handler).extract_card_payment_notice(artifact)
    body, timeouts = observed[0]
    assert type(result) is CardPaymentNoticeCandidate
    assert result.model_dump(mode="json") == normal_case["expected"]
    assert body["model"] == "configured-model"
    assert body["reasoning"] == {"effort": "low"}
    assert body["store"] is False
    assert body["max_output_tokens"] == 4096
    assert set(timeouts.values()) == {3}
    format = body["text"]["format"]
    assert format["type"] == "json_schema" and format["strict"] is True
    assert format["schema"]["additionalProperties"] is False
    assert set(format["schema"]["required"]) == set(CardPaymentNoticeCandidate.model_fields)
    assert set(format["schema"]["properties"]) == set(CardPaymentNoticeCandidate.model_fields)
    content = body["input"][0]["content"][0]
    assert content["type"] == ("input_image" if image_input else "input_text")
    if image_input:
        assert content["image_url"].startswith("data:image/png;base64,")


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (429, "RATE_LIMIT"),
        (503, "PROVIDER_UNAVAILABLE"),
        (401, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_http_errors_do_not_expose_provider_details(make_provider, status_code, expected):
    provider = make_provider(
        lambda request: httpx.Response(
            status_code,
            json={
                "error": {"message": "PRIVATE_PROVIDER_RESPONSE", "type": "test"},
            },
        )
    )
    with pytest.raises(AnalyzerError) as caught:
        provider.extract_card_payment_notice(SemanticInput(text="synthetic input"))
    assert caught.value.code == expected
    assert "PRIVATE" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_timeout_is_safe_and_never_falls_back_to_mock(make_provider):
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("PRIVATE_TIMEOUT", request=request)

    with pytest.raises(AnalyzerError) as caught:
        make_provider(handler).extract_card_payment_notice(SemanticInput(text="synthetic input"))
    assert caught.value.code == "TIMEOUT"
    assert len(calls) == 1
    assert "PRIVATE" not in str(caught.value)


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"refusal": True}, "REFUSAL"),
        ({"status": "incomplete", "empty": True}, "INCOMPLETE_OUTPUT"),
        ({"empty": True}, "INCOMPLETE_OUTPUT"),
        ({"status": "failed", "empty": True}, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_response_failures(make_provider, normal_case, kwargs, expected):
    body = response_body(normal_case["expected"], **kwargs)
    with pytest.raises(AnalyzerError) as caught:
        make_provider(lambda request: httpx.Response(200, json=body)).extract_card_payment_notice(
            SemanticInput(text=normal_case["text"])
        )
    assert caught.value.code == expected
    assert "PRIVATE" not in str(caught.value)


def test_incomplete_truncated_json_keeps_incomplete_error(make_provider, normal_case):
    body = response_body(normal_case["expected"], status="incomplete")
    body["output"][0]["content"][0]["text"] = '{"amount_minor":154'
    with pytest.raises(AnalyzerError) as caught:
        make_provider(lambda request: httpx.Response(200, json=body)).extract_card_payment_notice(
            SemanticInput(text=normal_case["text"])
        )
    assert caught.value.code == "INCOMPLETE_OUTPUT"


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_minor": "154000"},
        {"amount_minor": True},
        {"amount_minor": 0},
        {"amount_minor": -1},
        {"amount_minor": 1.5},
        {"confidence": "0.98"},
        {"confidence": 1.1},
        {"confidence": True},
        {"approved_at": "2026-09-03T12:14:00"},
        {"currency": "krw"},
        {"merchant": "  "},
        {"masked_card": "1234567890123456"},
        {"verification_status": "VERIFIED"},
        {"lifecycle_status": "ACTIVE"},
        {"reason_codes": []},
        {"authenticity_score": 0.99},
        {"transaction_id": 123},
        {"transaction_id": None},
        {"missing_fields": ["verification_status"]},
    ],
)
def test_schema_mismatch_is_strict_and_safe(make_provider, normal_case, changes):
    body = response_body({**normal_case["expected"], **changes})
    with pytest.raises(AnalyzerError) as caught:
        make_provider(lambda request: httpx.Response(200, json=body)).extract_card_payment_notice(
            SemanticInput(text=normal_case["text"])
        )
    assert caught.value.code == "SCHEMA_MISMATCH"


@pytest.mark.parametrize("body", [{"output": 7}, [1, 2], {"status": "completed", "output": [1]}])
def test_malformed_envelope_is_safe(make_provider, body):
    with pytest.raises(AnalyzerError) as caught:
        make_provider(lambda request: httpx.Response(200, json=body)).extract_card_payment_notice(
            SemanticInput(text="synthetic input")
        )
    assert caught.value.code == "SCHEMA_MISMATCH"


def test_missing_transaction_id_is_not_invented(make_provider, cases):
    case = next(item for item in cases if item["id"] == "readme_missing_transaction")
    provider = make_provider(
        lambda request: httpx.Response(200, json=response_body(case["expected"]))
    )
    candidate = provider.extract_card_payment_notice(SemanticInput(text=case["text"]))
    assert candidate.transaction_id is None
    assert candidate.missing_fields == ["transaction_id"]


def test_low_confidence_domain_gate(make_provider, normal_case):
    body = response_body({**normal_case["expected"], "confidence": 0.2})
    provider = make_provider(lambda request: httpx.Response(200, json=body))
    with pytest.raises(AnalyzerError) as caught:
        SemanticInterface(provider).analyze_card_payment_notice(
            SemanticInput(text=normal_case["text"])
        )
    assert caught.value.code == "LOW_CONFIDENCE"


def test_retries_are_bounded_to_three_attempts(make_provider):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(
            429, headers={"retry-after-ms": "1"}, json={"error": {"message": "limit"}}
        )

    with pytest.raises(AnalyzerError) as caught:
        make_provider(handler, max_retries=2).extract_card_payment_notice(
            SemanticInput(text="synthetic")
        )
    assert caught.value.code == "RATE_LIMIT"
    assert len(calls) == 3
