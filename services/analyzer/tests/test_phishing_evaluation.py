"""Evaluation denominators, split isolation and failure accounting, not model performance."""

import json
from pathlib import Path

import pytest
from originproof_analyzer.phishing_evaluation import (
    classification_metrics,
    evaluate_phishing,
    load_corpus,
)

CORPUS = (
    Path(__file__).resolve().parents[3] / "fixtures/synthetic/phishing_sources_v1.json"
)


def test_sixty_source_draft_has_proposed_24_36_split_and_no_cross_split_variants():
    manifest = load_corpus(CORPUS)
    assert manifest["review_status"] == "DRAFT_REVIEW_REQUIRED"
    assert manifest["input_selection"] == "UNDECIDED"
    assert manifest["labels_human_reviewed"] is False


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
    expected = [
        item["text"] for item in draft["cases"] if item["split"] == "development"
    ]
    assert seen == expected
    assert result["total"] == result["failures"] == 24
    assert result["abstentions"] == 0
    assert result["classification"]["macro_f1"] == 0
    assert result["live_model_evaluated"] is False
    assert "PRIVATE_PROVIDER_PAYLOAD" not in json.dumps(result)
    assert result["evidence"]["grounding_ratio"] is None
