"""D development-image evaluator with explicit callbacks; CLI only plans, never calls a model."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from statistics import median
from time import perf_counter

from originproof_core.wallet_contract import AnalysisReport

from .conversion_metrics import summarize_text_cases
from .converted_inputs import ConvertedText, analyze_conversion, prepare_conversion
from .errors import AnalyzerError, AnalyzerErrorCode
from .input_asset_pack import DEFAULT_CORPUS, DEFAULT_PACK, check_pack
from .inputs import SemanticInput
from .phishing_evaluation import classification_metrics


async def evaluate_document_images(
    corpus: Path = DEFAULT_CORPUS,
    pack: Path = DEFAULT_PACK,
    *,
    converter: Callable[[SemanticInput], Awaitable[ConvertedText | dict]] | None = None,
    processor: Callable[[str], Awaitable[AnalysisReport]] | None = None,
    remaining_seconds: float = 180,
) -> dict:
    """Pass bytes to converter, only converted text to processor; never labels/references.

    Callbacks are caller-owned. This is neither an API upload route nor paid-call
    authorization. Default invocation validates assets and plans without invoking either.
    """
    if (converter is None) != (processor is None):
        raise ValueError("converter and processor must be selected together")
    if (
        isinstance(remaining_seconds, bool)
        or not isinstance(remaining_seconds, int | float)
        or not 0 < remaining_seconds <= 180
    ):
        raise ValueError("invalid per-image deadline")
    check_pack(corpus, pack)
    manifest_path = pack / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    selected = [case for case in manifest["cases"] if case.get("image_asset")]
    rows, text_cases, durations = [], [], []
    for case in selected:
        row = {
            "id": case["source_id"],
            "expected": case["label_from_text"],
            "predicted": None,
            "status": "NOT_RUN",
            "error_code": None,
            "validated_quotes": 0,
            "llm_quotes": 0,
            "rule_quotes": 0,
            "model_unavailable_or_rejected": None,
            "mock_replay": None,
            "source_expected_quotes_covered": 0,
            "expected_quote_count": len(case["source_expected_evidence"]),
        }
        hypothesis = None
        if converter is not None:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            loop = asyncio.get_running_loop()
            deadline = loop.time() + remaining_seconds
            started = perf_counter()
            row["status"] = "CONVERSION_FAILED"
            try:
                asset = pack / case["image_asset"]["path"]
                artifact = SemanticInput(
                    image_base64=base64.b64encode(asset.read_bytes()).decode(),
                    image_media_type="image/png",
                )
                async with asyncio.timeout_at(deadline):
                    converted = ConvertedText.model_validate(await converter(artifact))
                    if converted.kind != "DOCUMENT_IMAGE":
                        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
                    prepared = prepare_conversion(converted)
                    if loop.time() >= deadline:
                        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT)
                    if task is not None and task.cancelling():
                        raise asyncio.CancelledError
                    hypothesis = prepared.text
                    row["status"] = "ANALYSIS_FAILED"
                    result = await analyze_conversion(
                        converted, processor, remaining_seconds=deadline - loop.time()
                    )
                if loop.time() >= deadline:
                    raise AnalyzerError(AnalyzerErrorCode.TIMEOUT)
                if task is not None and task.cancelling():
                    raise asyncio.CancelledError
                row.update(
                    predicted=result.report.risk_level,
                    status="COMPLETED",
                    validated_quotes=len(result.report.evidence),
                    llm_quotes=sum(item.source == "LLM" for item in result.report.evidence),
                    rule_quotes=sum(item.source == "RULE" for item in result.report.evidence),
                    model_unavailable_or_rejected=any(
                        item.startswith("LLM_ANALYSIS_UNAVAILABLE:")
                        for item in result.report.limitations
                    ),
                    mock_replay="MOCK_REPLAY_NOT_MODEL_PERFORMANCE" in result.report.limitations,
                    source_expected_quotes_covered=sum(
                        any(expected["quote"] in item.quote for item in result.report.evidence)
                        for expected in case["source_expected_evidence"]
                    ),
                )
            except AnalyzerError as error:
                row["error_code"] = error.code.value
            except TimeoutError:
                row["error_code"] = "TIMEOUT"
            except ValueError as error:
                row["error_code"] = (
                    "GROUNDING_MISMATCH"
                    if str(error) == "GROUNDING_MISMATCH"
                    else "SCHEMA_MISMATCH"
                )
            except Exception:
                row["error_code"] = "PROVIDER_UNAVAILABLE"
            durations.append(perf_counter() - started)
        rows.append(row)
        text_cases.append(
            {"id": case["source_id"], "reference": case["reference_text"], "hypothesis": hypothesis}
        )
    # Preserve source/asset identity across awaited callbacks as well as before the run.
    check_pack(corpus, pack)
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("image manifest changed during evaluation")
    executed = converter is not None
    return {
        "version": "v5-d-document-evaluation-0.1",
        "scope": "CALLBACK_EVALUATION_NOT_VERIFIED_AS_LIVE" if executed else "OFFLINE_PLAN_NOT_RUN",
        "source_fixture_sha256": manifest["source_fixture_sha256"],
        "asset_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "split": "development",
        "selected_images": len(selected),
        "excluded_text_only_ids": [
            c["source_id"] for c in manifest["cases"] if not c.get("image_asset")
        ],
        "completed": sum(row["status"] == "COMPLETED" for row in rows),
        "failed": sum(row["status"].endswith("FAILED") for row in rows),
        "not_run": sum(row["status"] == "NOT_RUN" for row in rows),
        "conversion": summarize_text_cases(text_cases) if executed else None,
        "combined_classification": classification_metrics(rows) if executed else None,
        "pipeline_latency_seconds_all_attempts": {
            "timed_cases": len(durations),
            "p50": median(durations) if durations else None,
            "p95": sorted(durations)[max(0, (95 * len(durations) + 99) // 100 - 1)]
            if durations
            else None,
        },
        "pixel_region_accuracy": "NOT_EVALUATED; NO_PIXEL_GROUND_TRUTH",
        "evidence_scope": (
            "CONVERTED_TEXT_QUOTES; SOURCE_QUOTE_COVERAGE_IS_NOT_PIXEL_OR_ORIGINAL_OFFSET_ACCURACY"
        ),
        "modality_human_review": "PENDING; TEXT_LABEL_REVIEW_DOES_NOT_APPROVE_IMAGE_QUALITY",
        "paid_calls": None if executed else 0,
        "holdout_predictions": 0,
        "input_support_activated": False,
        "acceptance_status": "REQUIRES_HUMAN_REVIEW_NOT_PRODUCT_ACCEPTANCE",
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    content = (
        json.dumps(asyncio.run(evaluate_document_images()), ensure_ascii=False, indent=2) + "\n"
    )
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(content)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
