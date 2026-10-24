"""Evaluation-only, pre-grounding candidate counts; never persist quotes or provider payloads."""

from collections import Counter

from originproof_core.wallet_contract import AnalysisEvidence, AnalysisReport
from pydantic import ValidationError


def candidate_evidence_counts(text: str, candidates: list, expected: list[dict]) -> Counter:
    """Count every candidate, including rejected ones; annotations never go to the provider."""
    counts = Counter(candidate_quote_count=len(candidates))
    located, seen = [], set()
    for candidate in candidates:
        value = candidate.model_dump() if isinstance(candidate, AnalysisEvidence) else candidate
        quote = value.get("quote") if isinstance(value, dict) else None
        counts["matched_candidate_quote_count"] += bool(
            isinstance(quote, str) and quote and quote in text
        )
        try:
            item = AnalysisEvidence.model_validate(value, strict=True)
        except (TypeError, ValueError, ValidationError):
            counts["invalid_candidate_count"] += 1
            continue
        identity = (item.quote, item.start_offset, item.end_offset)
        counts["duplicate_candidate_count"] += identity in seen
        seen.add(identity)
        start, end = item.start_offset, item.end_offset
        if (
            item.source == "LLM"
            and item.page is None
            and item.start_ms is None
            and item.end_ms is None
            and start is not None
            and end is not None
            and 0 <= start < end <= len(text)
            and text[start:end] == item.quote
        ):
            counts["located_candidate_count"] += 1
            located.append(item)
    # Each annotation contributes at most once, even if the provider duplicates its quote.
    for annotation in expected:
        counts["covered_span_count"] += any(
            item.start_offset <= annotation["start_offset"]
            and item.end_offset >= annotation["end_offset"]
            for item in located
        )
        counts["exact_span_match_count"] += any(
            item.start_offset == annotation["start_offset"]
            and item.end_offset == annotation["end_offset"]
            and item.quote == annotation["quote"]
            for item in located
        )
    return counts


class CandidateEvidenceObserver:
    """Serial evaluation adapter: retain numeric counts only, before analyzer fallback/repair."""

    def __init__(self, provider):
        self.provider = provider
        self.provider_name = provider.provider_name
        self.model = provider.model
        self.expected = []
        self.counts = Counter()

    async def analyze_phishing(self, text):
        value = await self.provider.analyze_phishing(text)
        candidates = (
            value.evidence
            if isinstance(value, AnalysisReport)
            else value.get("evidence")
            if isinstance(value, dict)
            else None
        )
        if isinstance(candidates, list):
            self.counts["observed_cases"] += 1
            self.counts.update(candidate_evidence_counts(text, candidates, self.expected))
        else:
            self.counts["unreadable_reports"] += 1
        return value

    def metrics(self, *, expected_spans: int, total_cases: int) -> dict:
        counts = self.counts
        total = counts["candidate_quote_count"]
        observed = counts["observed_cases"]
        fields = (
            "candidate_quote_count",
            "matched_candidate_quote_count",
            "located_candidate_count",
            "invalid_candidate_count",
            "duplicate_candidate_count",
            "covered_span_count",
            "exact_span_match_count",
            "observed_cases",
            "unreadable_reports",
        )
        return {
            "status": "COMPLETE"
            if observed == total_cases
            else "PARTIAL"
            if observed
            else "NOT_EVALUATED",
            "scope": "PRE_GROUNDING_PROVIDER_EVIDENCE_NOT_RAW_WIRE_OR_MODEL_ACCURACY",
            **{name: counts[name] for name in fields},
            "total_cases": total_cases,
            "grounding_ratio": counts["matched_candidate_quote_count"] / total if total else None,
            "location_accuracy": counts["located_candidate_count"] / total if total else None,
            "expected_span_count": expected_spans,
            "missing_span_count": expected_spans - counts["covered_span_count"],
            "missing_rate": (expected_spans - counts["covered_span_count"]) / expected_spans
            if expected_spans
            else None,
            "annotation_location_recall": counts["exact_span_match_count"] / expected_spans
            if expected_spans
            else None,
        }
