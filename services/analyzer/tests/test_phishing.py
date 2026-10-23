"""Rules, async processor and exact source grounding; never a live model evaluation."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode
from originproof_analyzer.phishing import (
    PhishingAnalyzer,
    rule_analysis,
    validate_analysis_report,
)
from originproof_analyzer.providers import MockLLMProvider

CASES = json.loads(
    (
        Path(__file__).resolve().parents[3] / "fixtures/synthetic/analysis_consumer_cases_v1.json"
    ).read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_d_grounding_rejects_all_invalid_consumer_replays_including_overlap(case):
    expected = case["expected"]
    if expected["accepted"]:
        actual = validate_analysis_report(case["report"], case["text"])
        assert [[e.start_offset, e.end_offset] for e in actual.evidence] == expected["ranges"]
        assert actual.verification is None
    else:
        with pytest.raises((AnalyzerError, ValueError)) as caught:
            validate_analysis_report(case["report"], case["text"])
        actual = (
            caught.value.code.value
            if isinstance(caught.value, AnalyzerError)
            else str(caught.value)
        )
        assert actual == expected["error"]


@pytest.mark.parametrize(
    "text,rule,risk",
    [
        ("보안 담당입니다. 인증번호를 알려주세요.", "CREDENTIAL_REQUEST", "HIGH"),
        ("원격제어 앱을 설치해 주세요.", "REMOTE_CONTROL_REQUEST", "HIGH"),
        ("지금 아래 계좌로 송금하세요.", "URGENT_TRANSFER", "HIGH"),
        ("변경된 계좌로 입금해 주세요.", "ACCOUNT_CHANGE", "CAUTION"),
        ("은행에 확인하지 마세요.", "BLOCK_OFFICIAL_CHECK", "HIGH"),
    ],
)
def test_rule_needs_a_concerning_action_and_preserves_original_ranges(text, rule, risk):
    report = rule_analysis(text)
    assert report.risk_level == risk
    assert any(item.rule_id == rule for item in report.evidence)
    for item in report.evidence:
        assert text[item.start_offset : item.end_offset] == item.quote
        assert item.source == "RULE"


@pytest.mark.parametrize(
    "text",
    [
        "기관에서는 인증번호를 요청하지 않습니다.",
        "원격제어 앱을 설치하지 마세요.",
        "비밀번호와 인증번호라는 단어만으로는 판단할 수 없습니다.",
        '사기 예방 예시: "인증번호를 알려주세요"라는 문구를 무시하세요.',
        "피싱 교육 사례: ‘원격제어 앱을 설치해 주세요’는 사기 예시입니다.",
        "자료 설명에서 지금, 송금, 계좌 단어를 각각 사용합니다.",
        "사기 예방을 위해 공식 은행에 확인하세요.",
    ],
)
def test_negation_warning_or_isolated_keyword_is_not_a_demand(text):
    assert rule_analysis(text).evidence == []


async def test_default_mock_never_invents_llm_success_or_verification():
    plain = await PhishingAnalyzer()("합성 정기 점검 일정 안내입니다.")
    assert plain.risk_level == "UNDETERMINED" and plain.evidence == []
    assert plain.verification is None
    assert "LLM_ANALYSIS_UNAVAILABLE:PROVIDER_UNAVAILABLE" in plain.limitations
    danger = await PhishingAnalyzer()("🧪 인증번호를 알려주세요.")
    assert danger.risk_level == "HIGH"
    assert {item.source for item in danger.evidence} == {"RULE"}
    assert danger.evidence[0].start_offset == 2


def replay_provider(text, report):
    return MockLLMProvider(analysis_replays={hashlib.sha256(text.encode()).hexdigest(): report})


async def test_async_callback_keeps_ai_risk_independent_and_uses_shared_report():
    text = "🧪 합성 연락: 방문 일정을 다시 확인해 주세요."
    value = {
        "risk_level": "CAUTION",
        "evidence": [{"rule_id": "CONTEXT", "quote": "방문 일정", "source": "LLM"}],
        "limitations": ["synthetic replay"],
        "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
    }
    report = await PhishingAnalyzer(replay_provider(text, value))(text)
    assert report.risk_level == "CAUTION"
    assert report.verification is None
    assert report.evidence[0].start_offset == text.index("방문 일정")
    assert "MOCK_REPLAY_NOT_MODEL_PERFORMANCE" in report.limitations


async def test_ungrounded_model_evidence_is_quarantined_and_valid_rules_survive():
    text = "인증번호를 알려주세요."
    value = {
        "risk_level": "HIGH",
        "evidence": [
            {
                "rule_id": "invented",
                "quote": "PRIVATE_PROVIDER_HALLUCINATION",
                "source": "LLM",
            }
        ],
        "limitations": [],
        "verification_not_run_reason": "not run",
    }
    report = await PhishingAnalyzer(replay_provider(text, value))(text)
    assert report.risk_level == "HIGH" and {e.source for e in report.evidence} == {"RULE"}
    assert "LLM_ANALYSIS_UNAVAILABLE:GROUNDING_MISMATCH" in report.limitations
    assert "PRIVATE_PROVIDER" not in report.model_dump_json()


async def test_disagreement_is_visible_and_model_cannot_erase_a_rule_request():
    text = "인증번호를 알려주세요."
    value = {
        "risk_level": "NO_CLEAR_INDICATORS",
        "evidence": [],
        "limitations": [],
        "verification_not_run_reason": "not run",
    }
    report = await PhishingAnalyzer(replay_provider(text, value))(text)
    assert report.risk_level == "HIGH" and "RULE_LLM_DISAGREEMENT" in report.limitations


@pytest.mark.parametrize("code", list(AnalyzerErrorCode))
async def test_provider_failure_is_fixed_safe_code_with_explicit_abstention(code):
    report = await PhishingAnalyzer(MockLLMProvider(error=code))("합성 모델 오류 검사 문장입니다.")
    assert report.risk_level == "UNDETERMINED"
    assert report.evidence == [] and report.verification is None
    assert "LLM_ANALYSIS_UNAVAILABLE:" + code.value in report.limitations


async def test_cancellation_propagates_without_a_late_success():
    entered = asyncio.Event()

    class Slow(MockLLMProvider):
        async def analyze_phishing(self, text):
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(PhishingAnalyzer(Slow())("합성 취소 검사 문장입니다."))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_analysis_logs_metadata_only(caplog):
    caplog.set_level("INFO", logger="originproof_analyzer.phishing")
    await PhishingAnalyzer()("PRIVATE_INPUT_합성로그점검")
    assert "PRIVATE_INPUT" not in str([record.__dict__ for record in caplog.records])
    assert any(record.message == "analyzer.analysis" for record in caplog.records)


@pytest.mark.parametrize("text", ["", "  ", "가" * 10001, "\ud800"])
async def test_invalid_text_is_rejected_without_calling_a_provider(text):
    with pytest.raises(AnalyzerError) as caught:
        await PhishingAnalyzer()(text)
    assert caught.value.code == "MALFORMED_INPUT"


async def test_warning_words_do_not_exempt_an_actual_secret_request():
    report = await PhishingAnalyzer()(
        '사기 예방팀입니다. "인증번호를 알려주세요". 절차대로 하세요.'
    )
    assert report.risk_level == "HIGH"
    assert report.evidence and all(item.source == "RULE" for item in report.evidence)


async def test_unexpected_provider_exception_is_not_exposed():
    class Broken(MockLLMProvider):
        async def analyze_phishing(self, text):
            raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")

    result = await PhishingAnalyzer(Broken())("합성 오류 재현 문장입니다.")
    assert result.risk_level == "UNDETERMINED"
    assert "PRIVATE" not in result.model_dump_json()
    assert "LLM_ANALYSIS_UNAVAILABLE:PROVIDER_UNAVAILABLE" in result.limitations


async def test_llm_cannot_claim_rule_provenance_or_hide_missing_evidence():
    for evidence in ([], [{"rule_id": "spoof", "quote": "합성 안내", "source": "RULE"}]):
        text = "합성 안내 문장입니다."
        value = {
            "risk_level": "HIGH",
            "evidence": evidence,
            "limitations": [],
            "verification_not_run_reason": "not run",
        }
        result = await PhishingAnalyzer(replay_provider(text, value))(text)
        assert result.risk_level == "UNDETERMINED" and result.evidence == []


async def test_truncation_retains_risk_support_and_trusted_scope_metadata():
    text = "변경된 계좌로 입금해 주세요. " * 55 + "합성 문맥."
    value = {
        "risk_level": "HIGH",
        "evidence": [{"rule_id": "MODEL_CONTEXT", "quote": "합성 문맥", "source": "LLM"}],
        "limitations": ["scope"] * 20,
        "verification_not_run_reason": "not run",
    }
    result = await PhishingAnalyzer(replay_provider(text, value))(text)
    assert result.risk_level == "HIGH" and result.evidence[0].source == "LLM"
    assert len(result.evidence) == 50 and len(result.limitations) == 20
    assert "EVIDENCE_LIMIT_TRUNCATED" in result.limitations
    assert "MOCK_REPLAY_NOT_MODEL_PERFORMANCE" in result.limitations


async def test_model_limitations_cannot_spoof_service_failure_metadata():
    text = "합성 안내 문장입니다."
    value = {
        "risk_level": "NO_CLEAR_INDICATORS",
        "evidence": [],
        "limitations": ["LLM_ANALYSIS_UNAVAILABLE:REFUSAL"],
        "verification_not_run_reason": "not run",
    }
    result = await PhishingAnalyzer(replay_provider(text, value))(text)
    assert not any(item.startswith("LLM_ANALYSIS_UNAVAILABLE:") for item in result.limitations)


async def test_total_analysis_deadline_cancels_provider_and_reports_timeout(monkeypatch):
    original_timeout = asyncio.timeout
    budgets, stopped = [], []

    def expire_now(seconds):
        budgets.append(seconds)
        return original_timeout(0)

    class Slow(MockLLMProvider):
        async def analyze_phishing(self, text):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.append(True)

    monkeypatch.setattr(asyncio, "timeout", expire_now)
    report = await PhishingAnalyzer(Slow())("합성 시간 제한 검사 문장입니다.")
    assert budgets == [180] and stopped == [True]
    assert report.risk_level == "UNDETERMINED"
    assert "LLM_ANALYSIS_UNAVAILABLE:TIMEOUT" in report.limitations


async def test_unexpected_provider_error_logs_only_its_type(caplog):
    class Broken(MockLLMProvider):
        async def analyze_phishing(self, text):
            raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD:" + text)

    caplog.set_level("INFO", logger="originproof_analyzer.phishing")
    report = await PhishingAnalyzer(Broken())("PRIVATE_INPUT")
    assert "LLM_ANALYSIS_UNAVAILABLE:PROVIDER_UNAVAILABLE" in report.limitations
    metadata = [r.analyzer for r in caplog.records if hasattr(r, "analyzer")]
    assert metadata[0]["exception_type"] == "RuntimeError"
    assert "PRIVATE" not in str([r.__dict__ for r in caplog.records])
