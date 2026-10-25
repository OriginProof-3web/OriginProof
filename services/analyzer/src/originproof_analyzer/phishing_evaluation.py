"""Synthetic text evaluation. The CLI uses mock/rules; callers can inject a provider."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import get_args

from originproof_core.wallet_contract import AnalysisReport

from .errors import AnalyzerError
from .evidence_evaluation import CandidateEvidenceObserver
from .phishing import RULE_VERSION, PhishingAnalyzer, validate_analysis_report
from .providers import ANALYSIS_PROMPT_VERSION, MockLLMProvider

LABELS = get_args(AnalysisReport.model_fields["risk_level"].annotation)


def load_corpus(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    cases = manifest["cases"]
    if manifest.get("source") != "synthetic" or len(cases) != 60:
        raise ValueError("expected 60 synthetic source cases")
    if len({case["id"] for case in cases}) != 60:
        raise ValueError("duplicate source case id")
    groups, original_splits = {}, {}
    for case in cases:
        if case["source"] != "synthetic" or case["label"] not in LABELS:
            raise ValueError("invalid source or label")
        if case["split"] not in {"development", "holdout"}:
            raise ValueError("invalid split")
        if not isinstance(case["text"], str) or not case["text"].strip():
            raise ValueError("missing source text")
        group = case["source_group"]
        if group in groups and groups[group] != case["split"]:
            raise ValueError("source variants cross development and holdout")
        groups[group] = case["split"]
        previous_split = original_splits.setdefault(case["text"], case["split"])
        if previous_split != case["split"]:
            raise ValueError("identical originals cross development and holdout")
        for quote in case["expected_evidence"]:
            start, end = quote["start_offset"], quote["end_offset"]
            if not 0 <= start < end <= len(case["text"]):
                raise ValueError("invalid annotated range")
            if case["text"][start:end] != quote["quote"]:
                raise ValueError("annotation differs from original text")
    counts = Counter((case["split"], case["label"]) for case in cases)
    if any(
        counts[split, label] != count
        for split, count in [
            ("development", 6),
            ("holdout", 9),
        ]
        for label in LABELS
    ):
        raise ValueError("expected four classes with 6 development and 9 holdout each")
    return manifest


def classification_metrics(rows: list[dict]) -> dict:
    matrix = {label: dict.fromkeys((*LABELS, "ERROR"), 0) for label in LABELS}
    for row in rows:
        matrix[row["expected"]][row["predicted"] or "ERROR"] += 1
    per_class = {}
    for label in LABELS:
        true_positive = matrix[label][label]
        support = sum(matrix[label].values())
        predicted = sum(matrix[other][label] for other in LABELS)
        recall = true_positive / support if support else None
        precision = true_positive / predicted if predicted else 0.0
        f1 = (2 * true_positive / (support + predicted)) if support + predicted else 0.0
        per_class[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return {
        "confusion_matrix": matrix,
        "per_class": per_class,
        "macro_f1": sum(item["f1"] for item in per_class.values()) / len(LABELS),
        "high_recall": per_class["HIGH"]["recall"],
    }


async def evaluate_phishing(
    path: Path, *, processor=None, provider=None, split="development", case_ids=None
) -> dict:
    manifest = load_corpus(path)
    if split not in {"development", "holdout"}:
        raise ValueError("select development or holdout explicitly")
    if processor is not None and provider is not None:
        raise ValueError("select processor or observed provider, not both")
    observer = CandidateEvidenceObserver(provider) if provider is not None else None
    analyzer = processor or PhishingAnalyzer(observer or MockLLMProvider())
    selected = [case for case in manifest["cases"] if case["split"] == split]
    if case_ids is not None:
        if (
            not case_ids
            or len(set(case_ids)) != len(case_ids)
            or not set(case_ids) <= {c["id"] for c in selected}
        ):
            raise ValueError("invalid selected case identity")
        selected = [case for case in selected if case["id"] in case_ids]
    rows, durations = [], []
    quote_total = expected_quotes = located_quotes = model_failures = 0
    grounding_rejected_reports = 0
    for case in selected:
        started = perf_counter()
        row = {
            "id": case["id"],
            "expected": case["label"],
            "predicted": None,
            "error_code": None,
        }
        expected_quotes += len(case["expected_evidence"])
        if observer is not None:
            observer.expected = case["expected_evidence"]
        try:
            # Only original text crosses the processor boundary, never labels or expected quotes.
            report = validate_analysis_report(await analyzer(case["text"]), case["text"])
            row["predicted"] = report.risk_level
            quote_total += len(report.evidence)
            located_quotes += sum(
                any(
                    item.start_offset <= expected["start_offset"]
                    and item.end_offset >= expected["end_offset"]
                    for item in report.evidence
                )
                for expected in case["expected_evidence"]
            )
            grounding_rejected_reports += (
                "LLM_ANALYSIS_UNAVAILABLE:GROUNDING_MISMATCH" in report.limitations
            )
            model_failures += any(
                value.startswith("LLM_ANALYSIS_UNAVAILABLE:") for value in report.limitations
            )
        except AnalyzerError as problem:
            row["error_code"] = problem.code.value
        except ValueError as problem:
            row["error_code"] = (
                str(problem)
                if str(problem)
                in {
                    "GROUNDING_MISMATCH",
                    "ANALYZER_AUTHORITY_VIOLATION",
                }
                else "SCHEMA_MISMATCH"
            )
        except Exception:
            row["error_code"] = "PROVIDER_UNAVAILABLE"
        grounding_rejected_reports += row["error_code"] == "GROUNDING_MISMATCH"
        durations.append(perf_counter() - started)
        rows.append(row)
    provider = getattr(analyzer, "provider", None)
    live = getattr(provider, "provider_name", "mock") == "openai"
    ordered = sorted(durations)
    return {
        "source": "synthetic",
        "evaluation_version": "v5-d-evaluation-0.3",
        "corpus_version": manifest["fixture_version"],
        "corpus_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "review_status": manifest["review_status"],
        "split": split,
        "total": len(rows),
        "scope": "Synthetic text; combined rule/provider pipeline, not real-world accuracy.",
        "live_model_evaluated": live,
        "model": getattr(provider, "model", None) if live else None,
        "prompt_version": ANALYSIS_PROMPT_VERSION,
        "rule_version": RULE_VERSION,
        "acceptance_status": (
            "LABELS_CONFIRMED_EXECUTION_REVIEW_REQUIRED"
            if manifest.get("labels_human_reviewed") is True
            else "DRAFT_REVIEW_REQUIRED"
        ),
        "paid_cost": None,
        "classification": classification_metrics(rows),
        "abstentions": sum(row["predicted"] == "UNDETERMINED" for row in rows),
        "failures": sum(row["error_code"] is not None for row in rows),
        "model_unavailable_or_rejected": model_failures,
        "evidence": {
            "validated_quote_count": quote_total,
            "output_safety_scope": "VALIDATED_OUTPUT_ONLY_NOT_CANDIDATE_ACCURACY",
            "grounding_rejected_reports": grounding_rejected_reports,
            "candidate_grounding": observer.metrics(
                expected_spans=expected_quotes, total_cases=len(rows)
            )
            if observer is not None
            else {
                "status": "NOT_EVALUATED",
                "reason": "RAW_PROVIDER_CANDIDATES_NOT_OBSERVED",
                "candidate_quote_count": None,
                "matched_candidate_quote_count": None,
                "grounding_ratio": None,
            },
            "expected_span_count": expected_quotes,
            "covered_span_count": located_quotes,
            "location_recall": located_quotes / expected_quotes if expected_quotes else None,
        },
        "protected_field_match": None,
        "protected_field_scope": "NOT_EVALUATED_BY_RISK_ONLY_CORPUS",
        "latency_seconds": {
            "scope": "selected processor end-to-end; not service/API latency",
            "p50": median(durations),
            "p95": ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)],
        },
        "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", choices=["development", "holdout"], default="development")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(evaluate_phishing(args.manifest, split=args.split))
    git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    result["code_sha"] = git.stdout.strip() if git.returncode == 0 else "UNAVAILABLE"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "split",
                    "total",
                    "live_model_evaluated",
                    "abstentions",
                    "failures",
                    "acceptance_status",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
