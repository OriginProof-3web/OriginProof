"""D fixture integrity only; these are not measured risk predictions or API results."""

import json
from pathlib import Path
from typing import get_args

import pytest
from originproof_core.wallet_contract import AnalysisReport
from pydantic import ValidationError

MANIFEST = json.loads(
    (Path(__file__).resolve().parents[3] / "fixtures/synthetic/analysis_consumer_cases_v1.json")
    .read_text(encoding="utf-8")
)
CASES = MANIFEST["cases"]


def test_consumer_manifest_preserves_unexecuted_synthetic_scope():
    assert MANIFEST["source"] == "synthetic"
    assert len({case["id"] for case in CASES}) == len(CASES) == 30
    assert all(case["source"] == "synthetic" for case in CASES)
    assert all(case["execution_status"] == "NOT_RUN" and case["basis"] for case in CASES)
    observed = {case["report"]["risk_level"] for case in CASES if case["expected"]["accepted"]}
    assert observed == set(get_args(AnalysisReport.model_fields["risk_level"].annotation))


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["expected"]["accepted"]], ids=lambda c: c["id"]
)
def test_accepted_fixture_quotes_match_exact_original_codepoint_ranges(case):
    report = AnalysisReport.model_validate(case["report"])
    assert report.verification is None and report.verification_not_run_reason
    assert len(report.evidence) == len(case["expected"]["ranges"])
    for evidence, (start, end) in zip(report.evidence, case["expected"]["ranges"], strict=True):
        assert 0 <= start < end <= len(case["text"])
        assert case["text"][start:end] == evidence.quote


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["expected"].get("error") == "SCHEMA_MISMATCH"
     and "minimum_contract_revision" not in c],
    ids=lambda c: c["id"],
)
def test_invalid_common_contract_replays_are_invalid_already_on_the_baseline(case):
    with pytest.raises(ValidationError):
        AnalysisReport.model_validate(case["report"])


def test_ambiguous_replay_covers_overlapping_occurrences():
    case = next(case for case in CASES if case["id"] == "DG12-overlapping-ambiguous-quote")
    quote = case["report"]["evidence"][0]["quote"]
    assert case["text"].count(quote) == 1
    assert case["text"].find(quote, case["text"].find(quote) + 1) >= 0
    assert case["expected"]["error"] == "GROUNDING_MISMATCH"
