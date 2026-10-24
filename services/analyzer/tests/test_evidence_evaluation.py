"""Pre-grounding denominators survive fallback, duplicate quotes and provider failure."""

import json
from pathlib import Path

import pytest
from originproof_analyzer.evidence_evaluation import (
    CandidateEvidenceObserver,
    candidate_evidence_counts,
)
from originproof_analyzer.phishing_evaluation import evaluate_phishing, load_corpus

CORPUS = Path(__file__).resolve().parents[3] / "fixtures/synthetic/phishing_sources_v1.json"


def evidence(quote="위험", start=2, end=4, **extra):
    return dict(
        rule_id="synthetic", quote=quote, start_offset=start, end_offset=end, source="LLM", **extra
    )


@pytest.mark.parametrize(
    ("candidate", "present", "located"),
    [
        (evidence(), 1, 1),
        (evidence("없는 인용", 0, 5), 0, 0),
        (evidence(start=0, end=2), 1, 0),
        (evidence(start=None, end=None), 1, 0),
        (evidence(start=True, end=4), 1, 0),
        (evidence(start=2, end=99), 1, 0),
        (evidence(page=1), 1, 0),
        ({"quote": "위험"}, 1, 0),
        ("malformed", 0, 0),
    ],
)
def test_candidate_string_presence_and_explicit_codepoint_location_are_separate(
    candidate, present, located
):
    # Emoji occupies one Python code point; UTF-16/byte offsets must not be treated as correct.
    counts = candidate_evidence_counts("😀 위험", [candidate], [evidence()])
    assert counts["candidate_quote_count"] == 1
    assert counts["matched_candidate_quote_count"] == present
    assert counts["located_candidate_count"] == located
    assert counts["covered_span_count"] == counts["exact_span_match_count"] == located


def test_duplicate_predictions_cannot_cover_an_annotation_twice():
    item = evidence()
    counts = candidate_evidence_counts("😀 위험", [item, item], [item])
    assert counts["candidate_quote_count"] == counts["located_candidate_count"] == 2
    assert counts["duplicate_candidate_count"] == 1
    assert counts["covered_span_count"] == counts["exact_span_match_count"] == 1


def test_repeated_or_overlapping_quotes_require_explicit_location():
    counts = candidate_evidence_counts(
        "하하하",
        [evidence("하하", None, None), evidence("하하", 1, 3)],
        [evidence("하하", 0, 2), evidence("하하", 1, 3)],
    )
    assert counts["matched_candidate_quote_count"] == 2
    assert counts["located_candidate_count"] == counts["covered_span_count"] == 1


def test_broad_quote_coverage_does_not_claim_exact_annotated_location():
    counts = candidate_evidence_counts("😀 위험", [evidence("😀 위험", 0, 4)], [evidence()])
    assert counts["covered_span_count"] == 1
    assert counts["exact_span_match_count"] == 0


class SyntheticProvider:
    provider_name, model = "mock", "synthetic-candidate-test"

    def __init__(self, *, empty=False, unavailable=False):
        self.seen = []
        self.empty, self.unavailable = empty, unavailable

    async def analyze_phishing(self, text):
        self.seen.append(text)
        if self.unavailable:
            raise RuntimeError("PRIVATE_PROVIDER_EXCEPTION")
        return {
            "risk_level": "UNDETERMINED",
            "evidence": [] if self.empty else [evidence("PRIVATE_ABSENT_QUOTE", 0, 20)],
            "limitations": [],
            "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
        }


async def test_observer_counts_all_rejected_candidates_without_exposing_them(caplog):
    provider = SyntheticProvider()
    result = await evaluate_phishing(CORPUS, provider=provider)
    counts = result["evidence"]["candidate_grounding"]
    assert counts["status"] == "COMPLETE"
    assert counts["observed_cases"] == counts["candidate_quote_count"] == 24
    assert counts["matched_candidate_quote_count"] == 0
    assert counts["grounding_ratio"] == counts["location_accuracy"] == 0
    assert counts["expected_span_count"] == counts["missing_span_count"] == 12
    assert counts["missing_rate"] == 1
    assert counts["annotation_location_recall"] == 0
    assert result["evidence"]["grounding_rejected_reports"] == 24
    assert result["evidence"]["validated_quote_count"] == 8  # Independently safe rule fallback.
    assert provider.seen == [
        c["text"] for c in load_corpus(CORPUS)["cases"] if c["split"] == "development"
    ]
    assert "PRIVATE_ABSENT_QUOTE" not in json.dumps(result) + caplog.text
    assert result["live_model_evaluated"] is False


@pytest.mark.parametrize("unavailable", [False, True])
async def test_zero_candidates_never_become_perfect_accuracy(unavailable):
    result = await evaluate_phishing(
        CORPUS, provider=SyntheticProvider(empty=True, unavailable=unavailable)
    )
    metrics = result["evidence"]["candidate_grounding"]
    assert metrics["status"] == ("NOT_EVALUATED" if unavailable else "COMPLETE")
    assert metrics["grounding_ratio"] is metrics["location_accuracy"] is None
    assert metrics["missing_span_count"] == 12
    assert "PRIVATE_PROVIDER_EXCEPTION" not in json.dumps(result)


async def test_unreadable_and_partial_provider_reports_are_not_complete():
    provider = SyntheticProvider()
    observer = CandidateEvidenceObserver(provider)
    observer.expected = [evidence()]
    await observer.analyze_phishing("😀 위험")
    metrics = observer.metrics(expected_spans=2, total_cases=2)
    assert metrics["status"] == "PARTIAL" and metrics["missing_span_count"] == 2

    async def malformed(text):
        return {"evidence": "PRIVATE_MALFORMED_PAYLOAD"}

    provider.analyze_phishing = malformed
    await observer.analyze_phishing("😀 위험")
    assert observer.metrics(expected_spans=2, total_cases=2)["unreadable_reports"] == 1


async def test_processor_and_observed_provider_cannot_silently_double_call():
    provider = SyntheticProvider()
    with pytest.raises(ValueError, match="select processor or observed provider"):
        await evaluate_phishing(CORPUS, processor=provider.analyze_phishing, provider=provider)
    assert provider.seen == []
