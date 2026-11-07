"""Evaluation denominators, split isolation and failure accounting, not model performance."""

import json
from pathlib import Path

import pytest
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.phishing_evaluation import (
    classification_metrics,
    evaluate_phishing,
    load_corpus,
)

CORPUS = Path(__file__).resolve().parents[3] / "fixtures/synthetic/phishing_sources_v1.json"


def test_sixty_reviewed_sources_keep_confirmed_24_36_split():
    manifest = load_corpus(CORPUS)
    assert manifest["review_status"] == "A_AND_C_CONFIRMED_UNCHANGED"
    assert manifest["input_selection"] == "TEXT"
    assert manifest["labels_human_reviewed"] is True


@pytest.mark.parametrize("change", ["leak", "duplicate", "bad_span", "count"])
def test_bad_or_leaking_evaluation_data_is_rejected(tmp_path, change):
    data = json.loads(CORPUS.read_text())
    if change == "leak":
        data["cases"][6]["source_group"] = data["cases"][0]["source_group"]
    elif change == "duplicate":
        data["cases"][1]["id"] = data["cases"][0]["id"]
    elif change == "bad_span":
        data["cases"][0]["expected_evidence"][0]["end_offset"] = 999
    else:
        data["cases"].pop()
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_corpus(path)


def test_failures_are_false_negatives_not_successful_abstention_predictions():
    metrics = classification_metrics(
        [
            {"expected": "HIGH", "predicted": "HIGH"},
            {"expected": "HIGH", "predicted": None},
            {"expected": "UNDETERMINED", "predicted": None},
        ]
    )
    assert metrics["high_recall"] == 0.5
    assert metrics["per_class"]["UNDETERMINED"]["recall"] == 0
    assert metrics["confusion_matrix"]["HIGH"]["ERROR"] == 1
    assert metrics["macro_f1"] == pytest.approx((2 / 3) / 4)


async def test_default_evaluation_only_runs_development_without_labels_in_processor_input():
    seen = []

    async def failed(text):
        seen.append(text)
        raise RuntimeError("PRIVATE_PROVIDER_PAYLOAD")

    result = await evaluate_phishing(CORPUS, processor=failed)
    draft = load_corpus(CORPUS)
    expected = [item["text"] for item in draft["cases"] if item["split"] == "development"]
    assert seen == expected
    assert result["total"] == result["failures"] == 24
    assert result["abstentions"] == 0
    assert result["classification"]["macro_f1"] == 0
    assert result["live_model_evaluated"] is False
    assert result["acceptance_status"] == "LABELS_CONFIRMED_EXECUTION_REVIEW_REQUIRED"
    assert "PRIVATE_PROVIDER_PAYLOAD" not in json.dumps(result)
    assert result["evidence"]["candidate_grounding"]["grounding_ratio"] is None
    assert result["evidence"]["expected_span_count"] == 12
    assert result["evidence"]["covered_span_count"] == 0


@pytest.mark.parametrize("quarantine", [False, True])
async def test_rejected_candidates_never_become_perfect_grounding_accuracy(quarantine):
    class Ungrounded:
        provider_name, model = "mock", None

        async def analyze_phishing(self, text):
            return {
                "risk_level": "HIGH",
                "evidence": [{"rule_id": "synthetic", "quote": "ABSENT_QUOTE", "source": "LLM"}],
                "limitations": [],
                "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
            }

    provider = Ungrounded()
    processor = PhishingAnalyzer(provider) if quarantine else provider.analyze_phishing
    result = await evaluate_phishing(CORPUS, processor=processor)
    evidence = result["evidence"]
    assert "grounding_ratio" not in evidence
    assert evidence["candidate_grounding"] == {
        "status": "NOT_EVALUATED",
        "reason": "RAW_PROVIDER_CANDIDATES_NOT_OBSERVED",
        "candidate_quote_count": None,
        "matched_candidate_quote_count": None,
        "grounding_ratio": None,
    }
    assert evidence["grounding_rejected_reports"] == 24
    assert evidence["expected_span_count"] == 12  # Failed cases remain in the denominator.
    assert evidence["output_safety_scope"] == "VALIDATED_OUTPUT_ONLY_NOT_CANDIDATE_ACCURACY"
    if quarantine:
        assert result["failures"] == 0
        assert result["model_unavailable_or_rejected"] == 24
        assert evidence["validated_quote_count"] == 8  # Only independently grounded rules survive.
        assert evidence["covered_span_count"] == 7
        assert evidence["location_recall"] == pytest.approx(7 / 12)
    else:
        assert result["failures"] == 24
        assert evidence["validated_quote_count"] == evidence["covered_span_count"] == 0
        assert evidence["location_recall"] == 0
