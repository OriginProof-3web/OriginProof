"""Constructed SDK failures/quotes, not retained model replies or a new quality evaluation."""

import json
from pathlib import Path

import httpx
import pytest
from openai import AsyncOpenAI
from originproof_analyzer.errors import AnalyzerError
from originproof_analyzer.phishing import PhishingAnalyzer, validate_analysis_report
from originproof_analyzer.phishing_evaluation import evaluate_phishing
from originproof_analyzer.providers import ANALYSIS_PROMPT_VERSION, OpenAILLMProvider
from originproof_analyzer.settings import AnalyzerSettings

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "fixtures/synthetic/phishing_sources_v1.json"
DEVELOPMENT = {
    c["id"]: c for c in json.loads(CORPUS.read_text())["cases"] if c["split"] == "development"
}


def constructed_report(quote=None, risk="CAUTION"):
    return {
        "risk_level": risk,
        "evidence": []
        if quote is None
        else [
            {
                "rule_id": "SYNTHETIC_CONTROL",
                "quote": quote,
                "source": "LLM",
                "start_offset": None,
                "end_offset": None,
                "page": None,
                "start_ms": None,
                "end_ms": None,
            }
        ],
        "limitations": [],
        "verification": None,
        "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
    }


def assert_quote_only_request(request):
    body = json.loads(request.content)
    schema = body["text"]["format"]["schema"]
    ref = schema["properties"]["evidence"]["items"]["$ref"].split("/")[-1]
    fields = schema["$defs"][ref]["properties"]
    for field in ("start_offset", "end_offset", "page", "start_ms", "end_ms"):
        assert fields[field]["type"] == "null"
    assert fields["source"]["const"] == "LLM"
    assert body["store"] is False and "tools" not in body
    return body


@pytest.mark.parametrize("case_id", ["DP-H01", "DP-H05", "DP-C01", "DP-C02"])
async def test_development_failure_shapes_use_exact_unique_quotes_not_guessed_numbers(
    case_id,
    response_body,
):
    case = DEVELOPMENT[case_id]
    quote = case["expected_evidence"][0]["quote"]
    # Construct the numeric error class; original raw model output was deliberately not kept.
    wrong = constructed_report(quote, case["label"])
    wrong["evidence"][0].update(start_offset=0, end_offset=len(quote))
    assert not case["text"].startswith(quote)
    with pytest.raises(ValueError, match="GROUNDING_MISMATCH"):
        validate_analysis_report(wrong, case["text"])
    requests = []

    def handler(request):
        body = assert_quote_only_request(request)
        requests.append(body["input"][0]["content"][0]["text"])
        return httpx.Response(200, json=response_body(constructed_report(quote, case["label"])))

    async with AsyncOpenAI(
        api_key="synthetic-placeholder",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        provider = OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
        result = await evaluate_phishing(CORPUS, provider=provider, case_ids=[case_id])
    assert requests == [case["text"]]  # Neither labels nor annotations cross the request boundary.
    assert result["prompt_version"] == ANALYSIS_PROMPT_VERSION == "phishing_analysis_v2"
    assert result["model_unavailable_or_rejected"] == 0
    assert result["evidence"]["candidate_grounding"]["located_candidate_count"] == 0
    post = result["evidence"]["validated_llm_locations"]
    assert (
        post["quote_count"] == post["covered_expected_spans"] == post["exact_expected_spans"] == 1
    )
    assert result["provider_offset_mode"] == "QUOTE_ONLY_DETERMINISTIC_UNIQUE_MATCH"


@pytest.mark.parametrize(
    "field,value",
    [
        ("start_offset", 0),
        ("end_offset", 4),
        ("page", 1),
        ("start_ms", 0),
        ("end_ms", 1),
        ("source", "RULE"),
    ],
)
async def test_text_wire_schema_rejects_even_structurally_plausible_numeric_locations(
    field,
    value,
    response_body,
):
    payload = constructed_report("합성 안내")
    payload["evidence"][0][field] = value
    async with AsyncOpenAI(
        api_key="synthetic-placeholder",
        max_retries=0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=response_body(payload))
            )
        ),
    ) as client:
        provider = OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
        with pytest.raises(AnalyzerError) as problem:
            await provider.analyze_phishing("합성 안내")
        assert problem.value.code == "SCHEMA_MISMATCH"


@pytest.mark.parametrize(
    "text,quote",
    [
        ("🧪 합성: 확인\t요청", "확인\t요청"),
        ("e\u0301 합성\n검토  안내", "검토  안내"),
        ("합성 👩‍💻: 제출 양식", "제출 양식"),
    ],
)
async def test_quote_only_unicode_and_whitespace_resolve_by_existing_exact_validator(
    text,
    quote,
    response_body,
):
    async with AsyncOpenAI(
        api_key="synthetic-placeholder",
        max_retries=0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=response_body(constructed_report(quote)))
            )
        ),
    ) as client:
        provider = OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
        result = await PhishingAnalyzer(provider)(text)
    item = next(e for e in result.evidence if e.source == "LLM")
    assert (item.start_offset, item.end_offset) == (
        text.index(quote),
        text.index(quote) + len(quote),
    )
    assert text[item.start_offset : item.end_offset] == quote


@pytest.mark.parametrize(
    "text,quote",
    [
        ("가가가", "가가"),
        ("검토 검토", "검토"),
        ("검토  요청", "검토 요청"),
        ("e\u0301", "é"),
        ("원문", "없는 문구"),
    ],
)
async def test_quote_only_keeps_ambiguous_normalized_or_absent_quotes_fail_closed(
    text,
    quote,
    response_body,
):
    async with AsyncOpenAI(
        api_key="synthetic-placeholder",
        max_retries=0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=response_body(constructed_report(quote)))
            )
        ),
    ) as client:
        provider = OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
        report = await PhishingAnalyzer(provider)(text)
    assert report.risk_level == "UNDETERMINED" and report.evidence == []
    assert "LLM_ANALYSIS_UNAVAILABLE:GROUNDING_MISMATCH" in report.limitations


def test_shared_validator_still_accepts_correct_disambiguated_explicit_spans():
    value = constructed_report("확인")
    value["evidence"][0].update(start_offset=3, end_offset=5)
    assert validate_analysis_report(value, "확인 확인").evidence[0].start_offset == 3
    value["evidence"][0].update(start_offset=1, end_offset=3)
    with pytest.raises(ValueError, match="GROUNDING_MISMATCH"):
        validate_analysis_report(value, "확인 확인")


@pytest.mark.parametrize("case_id", ["DP-U04", "DP-U06"])
@pytest.mark.parametrize("supplied_risk", ["UNDETERMINED", "NO_CLEAR_INDICATORS"])
async def test_schema_does_not_claim_to_fix_ambiguous_context_classification(
    case_id,
    supplied_risk,
    response_body,
):
    case = DEVELOPMENT[case_id]
    assert case["label"] == "UNDETERMINED"
    async with AsyncOpenAI(
        api_key="synthetic-placeholder",
        max_retries=0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json=response_body(constructed_report(risk=supplied_risk))
                )
            )
        ),
    ) as client:
        provider = OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
        report = await PhishingAnalyzer(provider)(case["text"])
    # A deliberately wrong NO_CLEAR reply still passes structural validation.
    # Only a new authorized live evaluation can establish whether the prompt helps.
    assert report.risk_level == supplied_risk
    assert report.verification is None


async def test_rule_fallback_cannot_inflate_validated_llm_location_counts(response_body):
    async with AsyncOpenAI(
        api_key="synthetic-placeholder",
        max_retries=0,
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json=response_body(constructed_report("ABSENT_CONTROL_QUOTE", risk="HIGH"))
                )
            )
        ),
    ) as client:
        provider = OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
        result = await evaluate_phishing(CORPUS, provider=provider, case_ids=["DP-H01"])
    assert result["cases"][0]["predicted"] == "HIGH"  # Trusted rule fallback remains.
    assert result["evidence"]["grounding_rejected_reports"] == 1
    assert result["evidence"]["covered_span_count"] == 1
    post = result["evidence"]["validated_llm_locations"]
    assert post["quote_count"] == post["exact_expected_spans"] == 0
    assert post["expected_span_count"] == 1 and post["location_recall"] == 0
