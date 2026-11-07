"""Controlled callbacks only; parent conftest blocks network and removes API keys."""

import asyncio
import base64
import hashlib
import json
import shutil

import pytest
from originproof_analyzer import document_evaluation as evaluation
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode
from originproof_analyzer.input_asset_pack import DEFAULT_CORPUS, DEFAULT_PACK
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider


@pytest.fixture
def replay():
    manifest = json.loads((DEFAULT_PACK / "manifest.json").read_text())
    text_by_image = {
        base64.b64encode((DEFAULT_PACK / row["image_asset"]["path"]).read_bytes()).decode(): row[
            "reference_text"
        ]
        for row in manifest["cases"]
        if row.get("image_asset")
    }
    calls = []

    async def converter(artifact):
        assert artifact.kind == "image" and artifact.text is None
        calls.append(artifact.image_base64)
        return {
            "kind": "DOCUMENT_IMAGE",
            "complete": True,
            "duration_ms": None,
            "segments": [
                {
                    "text": text_by_image[artifact.image_base64],
                    "page": 1,
                    "start_ms": None,
                    "end_ms": None,
                }
            ],
        }

    return converter, calls


async def test_default_is_a_plan_without_predictions_or_quality_scores():
    result = await evaluation.evaluate_document_images()
    assert (
        result["selected_images"],
        result["not_run"],
        result["completed"],
        result["failed"],
    ) == (23, 23, 0, 0)
    assert result["excluded_text_only_ids"] == ["DP-U05"]
    assert result["scope"] == "OFFLINE_PLAN_NOT_RUN"
    assert result["conversion"] is result["combined_classification"] is None
    assert result["paid_calls"] == result["holdout_predictions"] == 0
    assert not result["input_support_activated"]
    assert all(row["predicted"] is None and row["error_code"] is None for row in result["cases"])


async def test_replay_reuses_real_image_bytes_without_leaking_references_to_callbacks(replay):
    converter, calls = replay
    before = hashlib.sha256(DEFAULT_CORPUS.read_bytes()).hexdigest()
    result = await evaluation.evaluate_document_images(
        converter=converter, processor=PhishingAnalyzer(MockLLMProvider())
    )
    assert result["completed"] == len(calls) == 23
    assert result["failed"] == result["not_run"] == 0
    assert all(row["model_unavailable_or_rejected"] for row in result["cases"])
    assert sum(row["rule_quotes"] for row in result["cases"]) > 0
    assert sum(row["llm_quotes"] for row in result["cases"]) == 0
    assert result["conversion"]["corpus_character_error_rate"] == 0
    assert result["conversion"]["evaluated_cases"] == 23
    assert result["scope"] == "CALLBACK_EVALUATION_NOT_VERIFIED_AS_LIVE"
    assert result["paid_calls"] is None  # Scorer cannot infer a caller-owned callback's HTTP count.
    assert "NOT_EVALUATED" in result["pixel_region_accuracy"]
    assert "PENDING" in result["modality_human_review"]
    assert before == hashlib.sha256(DEFAULT_CORPUS.read_bytes()).hexdigest()
    assert "reference_text" not in json.dumps(result) and "image_base64" not in json.dumps(result)


@pytest.mark.parametrize(
    "mode,code",
    [
        ("partial", "INCOMPLETE_OUTPUT"),
        ("wrong_kind", "SCHEMA_MISMATCH"),
        ("exception", "PROVIDER_UNAVAILABLE"),
    ],
)
async def test_failed_conversion_stays_in_all_denominators_and_never_reaches_analysis(
    replay, mode, code
):
    convert, _ = replay
    analyzed = []

    async def converter(artifact):
        if mode == "exception":
            raise RuntimeError("PRIVATE_PROVIDER_DETAIL")
        value = await convert(artifact)
        if mode == "partial":
            value["complete"] = False
        else:
            value["kind"] = "AUDIO"
        return value

    async def processor(text):
        analyzed.append(text)
        pytest.fail("invalid converter result reached analysis")

    result = await evaluation.evaluate_document_images(converter=converter, processor=processor)
    assert result["failed"] == result["conversion"]["failed_cases"] == 23
    assert result["conversion"]["corpus_character_error_rate"] is None
    assert (
        sum(
            sum(row.values())
            for row in result["combined_classification"]["confusion_matrix"].values()
        )
        == 23
    )
    assert all(row["error_code"] == code and row["predicted"] is None for row in result["cases"])
    assert not analyzed and "PRIVATE_PROVIDER_DETAIL" not in json.dumps(result)


async def test_analysis_failure_preserves_conversion_metrics_but_is_not_a_correct_abstention(
    replay,
):
    converter, _ = replay

    async def processor(text):
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT)

    result = await evaluation.evaluate_document_images(converter=converter, processor=processor)
    assert result["conversion"]["corpus_character_error_rate"] == 0
    assert result["failed"] == 23 and result["completed"] == 0
    matrix = result["combined_classification"]["confusion_matrix"]
    assert matrix["UNDETERMINED"]["ERROR"] == 5
    assert matrix["UNDETERMINED"]["UNDETERMINED"] == 0
    assert all(row["status"] == "ANALYSIS_FAILED" for row in result["cases"])


async def test_changed_unicode_conversion_is_scored_against_reference_not_assumed_exact(replay):
    convert, _ = replay

    async def converter(artifact):
        value = await convert(artifact)
        value["segments"][0]["text"] = "😀 " + value["segments"][0]["text"]
        return value

    result = await evaluation.evaluate_document_images(
        converter=converter, processor=PhishingAnalyzer(MockLLMProvider())
    )
    assert result["completed"] == 23 and result["conversion"]["corpus_character_error_rate"] > 0
    assert result["cases"][0]["validated_quotes"] > 0
    assert result["cases"][0]["source_expected_quotes_covered"] == 1
    assert "NOT_PIXEL_OR_ORIGINAL_OFFSET" in result["evidence_scope"]


async def test_conversion_and_analysis_share_one_deadline(replay):
    convert, _ = replay
    analyzed = []

    async def converter(artifact):
        await asyncio.sleep(0.01)
        return await convert(artifact)

    async def processor(text):
        analyzed.append(text)
        pytest.fail("conversion used the entire deadline")

    result = await evaluation.evaluate_document_images(
        converter=converter, processor=processor, remaining_seconds=0.001
    )
    assert result["failed"] == 23 and not analyzed
    assert all(row["error_code"] == "TIMEOUT" for row in result["cases"])


async def test_cancellation_is_not_recorded_as_a_completed_failure(replay):
    async def cancelled(artifact):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await evaluation.evaluate_document_images(
            converter=cancelled, processor=PhishingAnalyzer(MockLLMProvider())
        )


async def test_tampered_asset_is_rejected_before_any_callback(tmp_path, replay):
    converter, calls = replay
    pack = tmp_path / "pack"
    shutil.copytree(DEFAULT_PACK, pack)
    manifest = json.loads((pack / "manifest.json").read_text())
    (pack / manifest["cases"][0]["image_asset"]["path"]).write_bytes(b"not an image")
    with pytest.raises(ValueError):
        await evaluation.evaluate_document_images(
            pack=pack, converter=converter, processor=PhishingAnalyzer(MockLLMProvider())
        )
    assert not calls


@pytest.mark.parametrize("seconds", [True, 0, float("nan"), float("inf"), 181])
async def test_invalid_deadline_never_invokes_callbacks(seconds, replay):
    converter, calls = replay
    with pytest.raises(ValueError):
        await evaluation.evaluate_document_images(
            converter=converter,
            processor=PhishingAnalyzer(MockLLMProvider()),
            remaining_seconds=seconds,
        )
    assert not calls


def test_cli_is_plan_only_and_preserves_existing_output(monkeypatch, tmp_path):
    path = tmp_path / "plan.json"
    monkeypatch.setattr("sys.argv", ["document_evaluation", "--output", str(path)])
    assert evaluation.main() == 0
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        evaluation.main()
    assert path.read_bytes() == original
