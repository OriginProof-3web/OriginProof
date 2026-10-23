"""Offline conversion scorers; no normalization, provider call or quality claim by default."""

from __future__ import annotations

import re

MAX_EDIT_CELLS = 4_000_000
MAX_CASES = 200


def text_error_metrics(reference: str, hypothesis: str | None) -> dict:
    """Unicode-code-point Levenshtein CER, not word accuracy or calibrated confidence."""
    if not isinstance(reference, str) or (
        hypothesis is not None and not isinstance(hypothesis, str)
    ):
        raise ValueError("text metric types")
    for text in (reference, hypothesis):
        if text is not None:
            if len(text) > 10_000:
                raise ValueError("text metric length")
            try:
                text.encode("utf-8")
            except UnicodeError:
                raise ValueError("text metric unicode") from None
    result = {
        "reference_characters": len(reference),
        "hypothesis_characters": len(hypothesis) if hypothesis is not None else None,
        "edit_distance": None,
        "character_error_rate": None,
        "exact_match": False,
    }
    if hypothesis is None:
        return result | {"status": "FAILED_NO_PREDICTION"}
    left, right = reference, hypothesis
    prefix = 0
    while prefix < min(len(left), len(right)) and left[prefix] == right[prefix]:
        prefix += 1
    left, right = left[prefix:], right[prefix:]
    suffix = 0
    while suffix < min(len(left), len(right)) and left[-suffix - 1] == right[-suffix - 1]:
        suffix += 1
    if suffix:
        left, right = left[:-suffix], right[:-suffix]
    if len(left) * len(right) > MAX_EDIT_CELLS:
        return result | {"status": "NOT_EVALUATED_RESOURCE_LIMIT"}
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(left) + 1))
    for row, char in enumerate(right, 1):
        current = [row]
        for column, other in enumerate(left, 1):
            current.append(
                min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (char != other))
            )
        previous = current
    distance = previous[-1]
    return result | {
        "status": "COMPUTED",
        "edit_distance": distance,
        "character_error_rate": distance / len(reference) if reference else None,
        "exact_match": reference == hypothesis,
    }


def summarize_text_cases(cases: list[dict]) -> dict:
    """Keep failed/resource-limited cases in coverage; never average only successful cases."""
    if len(cases) > MAX_CASES or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("metric case count/identity")
    results = []
    for case in cases:
        if not isinstance(case["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", case["id"]):
            raise ValueError("metric case id")
        results.append(
            {"id": case["id"], **text_error_metrics(case["reference"], case["hypothesis"])}
        )
    complete = bool(results) and all(row["status"] == "COMPUTED" for row in results)
    total = sum(row["reference_characters"] for row in results)
    distance = sum(row["edit_distance"] or 0 for row in results)
    return {
        "total_cases": len(results),
        "complete": complete,
        "evaluated_cases": sum(r["status"] == "COMPUTED" for r in results),
        "failed_cases": sum(r["status"] == "FAILED_NO_PREDICTION" for r in results),
        "resource_limited_cases": sum(
            r["status"] == "NOT_EVALUATED_RESOURCE_LIMIT" for r in results
        ),
        "reference_characters_all_cases": total,
        "corpus_character_error_rate": distance / total if complete and total else None,
        "results": results,
    }


def _interval(value) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"start_ms", "end_ms"}
        and type(value["start_ms"]) is int
        and type(value["end_ms"]) is int
        and 0 <= value["start_ms"] < value["end_ms"] <= 300_000
    )


def temporal_evidence_metrics(
    expected: list[dict], candidates: list[dict], *, tolerance_ms=2000
) -> dict:
    """Match intervals one-to-one; broad/duplicate spans cannot inflate recall."""
    if (
        type(tolerance_ms) is not int
        or not 0 <= tolerance_ms <= 2000
        or len(expected) > MAX_CASES
        or len(candidates) > MAX_CASES
    ):
        raise ValueError("time metric limits")
    if not all(_interval(item) for item in expected):
        raise ValueError("invalid expected time annotation")
    edges = [
        [
            index
            for index, item in enumerate(candidates)
            if _interval(item)
            and abs(target["start_ms"] - item["start_ms"]) <= tolerance_ms
            and abs(target["end_ms"] - item["end_ms"]) <= tolerance_ms
        ]
        for target in expected
    ]
    matched = {}

    def augment(target, seen):
        for candidate in edges[target]:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate not in matched or augment(matched[candidate], seen):
                matched[candidate] = target
                return True
        return False

    for target in range(len(expected)):
        augment(target, set())
    count = len(matched)
    return {
        "expected_spans": len(expected),
        "candidate_spans": len(candidates),
        "matched_spans": count,
        "missing_spans": len(expected) - count,
        "unmatched_candidates": len(candidates) - count,
        "invalid_candidates": sum(not _interval(item) for item in candidates),
        "precision": count / len(candidates) if candidates else None,
        "recall": count / len(expected) if expected else None,
        "tolerance_ms": tolerance_ms,
        "scope": "DECLARED_INTERVALS_NOT_WORD_TIMING_OR_ACTUAL_STT_QUALITY",
    }


def pixel_region_iou(
    expected: list[int], candidate: list[int], *, width: int, height: int
) -> float:
    """Raw top-left pixel rectangles [x0,y0,x1,y1); no assumed acceptance threshold."""
    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
        or width * height > 12_000_000
    ):
        raise ValueError("image metric dimensions")
    for box in (expected, candidate):
        if (
            not isinstance(box, list)
            or len(box) != 4
            or any(type(x) is not int for x in box)
            or not 0 <= box[0] < box[2] <= width
            or not 0 <= box[1] < box[3] <= height
        ):
            raise ValueError("invalid pixel rectangle")
    area = max(0, min(expected[2], candidate[2]) - max(expected[0], candidate[0]))
    area *= max(0, min(expected[3], candidate[3]) - max(expected[1], candidate[1]))
    union = (
        (expected[2] - expected[0]) * (expected[3] - expected[1])
        + (candidate[2] - candidate[0]) * (candidate[3] - candidate[1])
        - area
    )
    return area / union
