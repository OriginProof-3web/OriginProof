"""Controlled correct/incorrect inputs test scorers; no model or conversion performance measured."""

import json

import pytest
from originproof_analyzer.conversion_metrics import (
    summarize_text_cases,
    temporal_evidence_metrics,
    text_error_metrics,
)


@pytest.mark.parametrize(
    "reference,hypothesis,distance,rate",
    [
        ("합성 안내", "합성 안내", 0, 0),
        ("abc", "axc", 1, 1 / 3),
        ("abc", "ac", 1, 1 / 3),
        ("abc", "abxc", 1, 1 / 3),
        ("a", "aaaa", 3, 3),
        ("abc", "", 3, 1),
        ("", "a", 1, None),
        ("", "", 0, None),
        ("e\u0301", "é", 2, 1),
        ("🧪 a", "🧪a", 1, 1 / 3),
    ],
)
def test_character_errors_count_unicode_whitespace_and_insertions_without_score_clipping(
    reference, hypothesis, distance, rate
):
    result = text_error_metrics(reference, hypothesis)
    assert result["edit_distance"] == distance
    assert result["character_error_rate"] == rate
    assert result["exact_match"] == (reference == hypothesis)


def test_failures_and_resource_limits_prevent_a_success_only_corpus_average():
    result = summarize_text_cases(
        [
            {"id": "OK", "reference": "합성", "hypothesis": "합성"},
            {"id": "FAIL", "reference": "합성", "hypothesis": None},
            {"id": "LIMIT", "reference": "a" * 3000, "hypothesis": "b" * 3000},
        ]
    )
    assert result["total_cases"] == 3 and result["evaluated_cases"] == 1
    assert result["failed_cases"] == result["resource_limited_cases"] == 1
    assert result["corpus_character_error_rate"] is None and not result["complete"]
    assert "a" * 20 not in json.dumps(result)
    assert text_error_metrics("", None)["status"] == "FAILED_NO_PREDICTION"


def test_complete_corpus_uses_micro_character_denominator_and_empty_is_not_perfect():
    result = summarize_text_cases(
        [
            {"id": "A", "reference": "a", "hypothesis": "x"},
            {"id": "B", "reference": "abc", "hypothesis": "abc"},
        ]
    )
    assert result["corpus_character_error_rate"] == 0.25
    assert summarize_text_cases([])["corpus_character_error_rate"] is None
    assert not summarize_text_cases([])["complete"]


@pytest.mark.parametrize(
    "cases",
    [
        [{"id": "A", "reference": "a", "hypothesis": "a"}] * 2,
        [{"id": "../raw", "reference": "a", "hypothesis": "a"}],
    ],
)
def test_bad_case_identity_is_rejected(cases):
    with pytest.raises(ValueError):
        summarize_text_cases(cases)


@pytest.mark.parametrize(
    "reference,hypothesis", [(True, "a"), ("a", 1), ("\ud800", "a"), ("x" * 10001, "a")]
)
def test_invalid_text_cannot_get_a_score(reference, hypothesis):
    with pytest.raises(ValueError):
        text_error_metrics(reference, hypothesis)


def interval(start, end):
    return {"start_ms": start, "end_ms": end}


@pytest.mark.parametrize("delta,matched", [(2000, 1), (2001, 0)])
def test_two_second_threshold_checks_both_endpoints(delta, matched):
    result = temporal_evidence_metrics(
        [interval(1000, 3000)], [interval(1000 + delta, 3000 + delta)]
    )
    assert result["matched_spans"] == matched


def test_duplicates_invalid_and_overly_broad_candidates_remain_in_precision_denominator():
    result = temporal_evidence_metrics(
        [interval(1000, 3000)],
        [interval(1000, 3000), interval(1000, 3000), interval(0, 300_000), interval(True, 3000)],
    )
    assert result["matched_spans"] == 1 and result["precision"] == 0.25
    assert result["recall"] == 1 and result["invalid_candidates"] == 1
    assert result["unmatched_candidates"] == 3


def test_matching_does_not_depend_on_greedy_first_candidate_order():
    # First target can use either candidate; second target can use only the first.
    result = temporal_evidence_metrics(
        [interval(2000, 3000), interval(0, 1000)], [interval(1000, 2000), interval(4000, 5000)]
    )
    assert result["matched_spans"] == 2


def test_empty_time_denominators_do_not_produce_perfect_scores():
    result = temporal_evidence_metrics([], [])
    assert result["precision"] is result["recall"] is None
    assert temporal_evidence_metrics([interval(1, 2)], [])["missing_spans"] == 1


@pytest.mark.parametrize(
    "expected,tolerance",
    [([interval(2, 1)], 2000), ([interval(True, 2)], 2000), ([], 2001), ([], True)],
)
def test_invalid_annotations_or_loosened_tolerance_are_rejected(expected, tolerance):
    with pytest.raises(ValueError):
        temporal_evidence_metrics(expected, [], tolerance_ms=tolerance)


@pytest.mark.parametrize(
    "candidate,expected", [([0, 0, 10, 10], 1), ([10, 0, 20, 10], 0), ([5, 5, 15, 15], 1 / 7)]
)
def test_image_region_score_uses_explicit_pixel_frame_without_pass_threshold(candidate, expected):
    from originproof_analyzer.conversion_metrics import pixel_region_iou

    assert pixel_region_iou([0, 0, 10, 10], candidate, width=20, height=20) == expected


@pytest.mark.parametrize(
    "candidate", [[-1, 0, 1, 1], [0, 0, 21, 1], [0, 0, 0, 1], [False, 0, 1, 1]]
)
def test_invalid_pixel_locations_cannot_become_zero_error_measurements(candidate):
    from originproof_analyzer.conversion_metrics import pixel_region_iou

    with pytest.raises(ValueError):
        pixel_region_iou([0, 0, 10, 10], candidate, width=20, height=20)
