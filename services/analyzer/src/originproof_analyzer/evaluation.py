"""Deterministic synthetic-fixture evaluation; deliberately no live-provider option."""

import argparse
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from .errors import AnalyzerError
from .inputs import SemanticInput
from .providers import PROMPT_VERSION, MockLLMProvider
from .service import SemanticInterface
from .validation import EXTRACTED_FIELDS


def render_synthetic_notice(text: str) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (860, 500), "white")
    ImageDraw.Draw(image).multiline_text((24, 24), text, fill="black", spacing=12, font_size=22)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def evaluate(fixture_path: Path) -> dict:
    manifest = json.loads(fixture_path.read_text(encoding="utf-8"))
    if manifest.get("source") != "synthetic" or not manifest.get("cases"):
        raise ValueError("evaluation requires a nonempty synthetic fixture manifest")
    results = []
    field_matches = dict.fromkeys(EXTRACTED_FIELDS, 0)
    field_totals = dict.fromkeys(EXTRACTED_FIELDS, 0)
    present_matches = dict.fromkeys(EXTRACTED_FIELDS, 0)
    present_totals = dict.fromkeys(EXTRACTED_FIELDS, 0)

    def run_case(case, *, image_input=False):
        if case.get("source") != "synthetic":
            raise ValueError("every evaluation case must be synthetic")
        text = case["text"]
        provider = MockLLMProvider()
        artifact = SemanticInput(text=text)
        if image_input:
            data = render_synthetic_notice(text)
            provider = MockLLMProvider(image_replays={hashlib.sha256(data).hexdigest(): text})
            artifact = SemanticInput(
                image_base64=base64.b64encode(data).decode(),
                image_media_type="image/png",
            )
        result = {"id": case["id"], "input_kind": artifact.kind, "passed": False}
        try:
            candidate = SemanticInterface(provider).analyze_card_payment_notice(artifact)
            observed = candidate.model_dump(mode="json")
            expected = case.get("expected", {})
            result["passed"] = observed == expected
            for field in EXTRACTED_FIELDS:
                matched = field in expected and observed[field] == expected[field]
                field_matches[field] += int(matched)
                field_totals[field] += 1
                if expected.get(field) is not None:
                    present_matches[field] += int(matched)
                    present_totals[field] += 1
        except AnalyzerError as exc:
            result["error_code"] = exc.code.value
            result["passed"] = exc.code.value == case.get("expected_error")
        results.append(result)

    for case in manifest["cases"]:
        run_case(case)
    for case in manifest["cases"]:
        if case["id"] in {"normal", "amount_changed"}:
            run_case(case, image_input=True)

    return {
        "source": "synthetic",
        "provider": "mock",
        "model": "deterministic-template-v3",
        "prompt_version": PROMPT_VERSION,
        "live_model_evaluated": False,
        "confidence_is_calibrated": False,
        "candidate_outputs_are_unconfirmed": True,
        "artifact_comparison_performed": False,
        "image_mode": "fixture_replay_only",
        "scope": "Template and adapter contract tests, not OCR accuracy or model performance.",
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
        "fields": {
            name: {
                "matched": field_matches[name],
                "total": field_totals[name],
                "present_matched": present_matches[name],
                "present_total": present_totals[name],
            }
            for name in EXTRACTED_FIELDS
        },
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("fixtures/mvp/analyzer_cases.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.fixtures)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
