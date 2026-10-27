"""Post-conversion safety and actual analyzer replay; not OCR/STT accuracy or live calls."""

import asyncio
from copy import deepcopy

import pytest
from originproof_analyzer.converted_inputs import (
    ConversionSegment,
    ConvertedText,
    analyze_conversion,
    prepare_conversion,
)
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider


def image(*texts):
    return {
        "kind": "DOCUMENT_IMAGE",
        "complete": True,
        "segments": [{"text": t, "page": 1} for t in texts],
    }


def audio():
    return {
        "kind": "AUDIO",
        "complete": True,
        "duration_ms": 5000,
        "segments": [
            {"text": "합성 안내입니다.", "start_ms": 0, "end_ms": 1000},
            {"text": "🧪 인증번호를 알려주세요.", "start_ms": 3000, "end_ms": 4500},
        ],
    }


def report(quote, *, limitations=None):
    return {
        "risk_level": "CAUTION",
        "evidence": [{"rule_id": "SYNTHETIC_REPLAY", "quote": quote, "source": "LLM"}],
        "limitations": limitations or [],
        "verification_not_run_reason": "not run",
    }


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("post-conversion tests must not use network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_image_text_keeps_whitespace_unicode_and_declared_join_offsets():
    text = " 🧪 e\u0301 합성  "
    data = image(text, "두 번째 문장")
    original = deepcopy(data)
    value = prepare_conversion(data)
    assert value.text == text + "\n두 번째 문장"
    assert value.ranges[1].start == len(text) + 1
    assert value.ranges[0].page == 1
    assert text not in repr(value) and data == original


async def test_actual_rule_analyzer_maps_audio_quote_to_segment_not_word_time():
    value = audio()
    result = await analyze_conversion(value, PhishingAnalyzer(MockLLMProvider()))
    assert result.report.risk_level == "HIGH" and result.report.verification is None
    assert result.report.evidence[0].page is None and result.report.evidence[0].start_ms is None
    location = result.locations[0]
    assert location.segment_index == 1 and (location.start_ms, location.end_ms) == (3000, 4500)
    segment = value["segments"][1]["text"]
    assert segment[location.start_offset : location.end_offset] == result.report.evidence[0].quote
    assert "CONVERSION_ACCURACY_NOT_VERIFIED" in result.report.limitations
    assert "LOCATIONS_ARE_CONVERTER_SEGMENT_SPANS" in result.report.limitations
    assert segment not in repr(result)


async def test_cross_segment_quote_maps_both_segments_without_inventing_word_times():
    async def processor(text):
        assert text == "가\n나"
        return report(text)

    data = {
        "kind": "AUDIO",
        "complete": True,
        "duration_ms": 3000,
        "segments": [
            {"text": "가", "start_ms": 0, "end_ms": 1000},
            {"text": "나", "start_ms": 2000, "end_ms": 3000},
        ],
    }
    result = await analyze_conversion(data, processor)
    assert [(x.segment_index, x.start_offset, x.end_offset) for x in result.locations] == [
        (0, 0, 1),
        (1, 0, 1),
    ]
    assert [(x.start_ms, x.end_ms) for x in result.locations] == [(0, 1000), (2000, 3000)]


@pytest.mark.parametrize(
    "change",
    [
        "page_missing",
        "pdf_page",
        "image_time",
        "image_duration",
        "blank",
        "extra",
        "audio_page",
        "missing_time",
        "negative_time",
        "reversed_time",
        "overlap",
        "out_of_duration",
        "missing_duration",
        "over_max_duration",
        "bool_time",
        "bool_complete",
    ],
)
async def test_bad_converter_output_is_rejected_before_processor(change):
    data = (
        audio()
        if change.startswith(
            (
                "audio",
                "missing",
                "negative",
                "reversed",
                "overlap",
                "out_of",
                "over_max",
                "bool_time",
            )
        )
        else image("合成")
    )
    if change == "page_missing":
        data["segments"][0].pop("page")
    elif change == "pdf_page":
        data["segments"][0]["page"] = 2
    elif change == "image_time":
        data["segments"][0]["start_ms"] = 0
    elif change == "image_duration":
        data["duration_ms"] = 1000
    elif change == "blank":
        data["segments"][0]["text"] = "  "
    elif change == "extra":
        data["raw_provider_payload"] = "PRIVATE_SYNTHETIC"
    elif change == "audio_page":
        data["segments"][0]["page"] = 1
    elif change == "missing_time":
        data["segments"][0].pop("end_ms")
    elif change == "negative_time":
        data["segments"][0]["start_ms"] = -1
    elif change == "reversed_time":
        data["segments"][0]["start_ms"] = 1000
    elif change == "overlap":
        data["segments"][1]["start_ms"] = 999
    elif change == "out_of_duration":
        data["segments"][1]["end_ms"] = 5001
    elif change == "missing_duration":
        data.pop("duration_ms")
    elif change == "over_max_duration":
        data["duration_ms"] = 300001
    elif change == "bool_time":
        data["segments"][0]["start_ms"] = False
    else:
        data["complete"] = 1

    async def forbidden(text):
        raise AssertionError("invalid conversion must not be analyzed")

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(data, forbidden)
    assert exc.value.code == AnalyzerErrorCode.SCHEMA_MISMATCH
    assert "PRIVATE_SYNTHETIC" not in str(exc.value)


@pytest.mark.parametrize("data", [image(), image("합성") | {"complete": False}])
async def test_incomplete_or_unreadable_conversion_never_produces_a_risk_result(data):
    async def forbidden(text):
        raise AssertionError("incomplete output must not be analyzed")

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(data, forbidden)
    assert exc.value.code == AnalyzerErrorCode.INCOMPLETE_OUTPUT


@pytest.mark.parametrize("extra,accepted", [(0, True), (1, False)])
def test_total_ten_thousand_limit_includes_join_separators(extra, accepted):
    data = image("가" * 5999, "나" * (4000 + extra))
    if accepted:
        assert len(prepare_conversion(data).text) == 10_000
    else:
        with pytest.raises(AnalyzerError) as exc:
            prepare_conversion(data)
        assert exc.value.code == AnalyzerErrorCode.MALFORMED_INPUT


def test_surrogates_and_constructed_invalid_nested_models_cannot_bypass_validation():
    with pytest.raises(AnalyzerError) as exc:
        prepare_conversion(image("\ud800"))
    assert exc.value.code == AnalyzerErrorCode.SCHEMA_MISMATCH
    value = ConvertedText.model_construct(
        kind="DOCUMENT_IMAGE",
        complete=True,
        segments=[ConversionSegment.model_construct(text="合成", page=True)],
    )
    with pytest.raises(AnalyzerError) as exc:
        prepare_conversion(value)
    assert exc.value.code == AnalyzerErrorCode.SCHEMA_MISMATCH


@pytest.mark.parametrize("budget", [0, -1, 181, True, float("nan"), float("inf"), "1"])
async def test_invalid_remaining_budget_never_invokes_processor(budget):
    async def forbidden(text):
        raise AssertionError("invalid deadline must not trigger analysis")

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(image("合成"), forbidden, remaining_seconds=budget)
    assert exc.value.code == AnalyzerErrorCode.MALFORMED_INPUT


@pytest.mark.parametrize("ignore_cancel", [False, True])
async def test_timeout_or_late_result_cannot_become_success(ignore_cancel):
    async def processor(text):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if not ignore_cancel:
                raise
            return report(text)

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(image("合成"), processor, remaining_seconds=0.01)
    assert exc.value.code == AnalyzerErrorCode.TIMEOUT


async def test_outer_cancellation_propagates_to_processor():
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def processor(text):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    task = asyncio.create_task(analyze_conversion(image("合成"), processor))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()


async def test_provider_details_are_hidden_and_known_error_code_is_preserved(caplog):
    async def failed(text):
        raise RuntimeError("PRIVATE_SYNTHETIC_PROVIDER " + text)

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(image("合成"), failed)
    assert exc.value.code == AnalyzerErrorCode.PROVIDER_UNAVAILABLE
    assert "PRIVATE_SYNTHETIC_PROVIDER" not in str(exc.value) + caplog.text

    async def refusal(text):
        raise AnalyzerError(AnalyzerErrorCode.REFUSAL)

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(image("合成"), refusal)
    assert exc.value.code == AnalyzerErrorCode.REFUSAL


@pytest.mark.parametrize("quote", ["없는 원문", "\n"])
async def test_absent_quote_or_join_separator_is_not_media_grounding(quote):
    async def processor(text):
        return report(quote)

    with pytest.raises(ValueError, match="^GROUNDING_MISMATCH$"):
        await analyze_conversion(image("가", "나"), processor)


async def test_scope_notices_cannot_be_lost_at_shared_limitation_limit():
    async def processor(text):
        return report(text, limitations=["scope"] * 20)

    result = await analyze_conversion(image("합성 자료"), processor)
    assert len(result.report.limitations) == 20
    assert result.report.limitations[:3] == [
        "CONVERSION_ACCURACY_NOT_VERIFIED",
        "LOCATIONS_ARE_CONVERTER_SEGMENT_SPANS",
        "LIMITATIONS_LIMIT_TRUNCATED",
    ]


async def test_time_spent_grounding_output_is_included_in_remaining_deadline(monkeypatch):
    import time

    import originproof_analyzer.converted_inputs as module

    validate = module.validate_analysis_report

    def slow_validation(value, text):
        time.sleep(0.02)
        return validate(value, text)

    monkeypatch.setattr(module, "validate_analysis_report", slow_validation)

    async def processor(text):
        return report(text)

    with pytest.raises(AnalyzerError) as exc:
        await analyze_conversion(image("합성 자료"), processor, remaining_seconds=0.01)
    assert exc.value.code == AnalyzerErrorCode.TIMEOUT


async def test_processor_swallowing_external_cancel_cannot_publish_success():
    started = asyncio.Event()

    async def processor(text):
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            return report(text)

    task = asyncio.create_task(analyze_conversion(image("합성 자료"), processor))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_pending_external_cancel_does_not_start_a_processor():
    calls = 0

    async def processor(text):
        nonlocal calls
        calls += 1
        return report(text)

    async def pending():
        asyncio.current_task().cancel()
        await analyze_conversion(image("합성 자료"), processor)

    task = asyncio.create_task(pending())
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls == 0
