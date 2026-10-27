"""Export the existing synthetic corpus for A/C review; no provider or predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .phishing_evaluation import load_corpus

MODALITIES = ("TEXT", "DOCUMENT_IMAGE")


def build_packet(corpus_path: Path, self_review_path: Path) -> dict:
    corpus = load_corpus(corpus_path)
    review = json.loads(self_review_path.read_text(encoding="utf-8"))
    corpus_hash = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    if review.get("source_fixture_sha256") != corpus_hash:
        raise ValueError("self-review does not match source corpus")
    rows = review["cases"]
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != 60 or len(rows) != 60 or set(by_id) != {c["id"] for c in corpus["cases"]}:
        raise ValueError("self-review must cover each source exactly once")
    reviewed = corpus.get("labels_human_reviewed") is True
    confirmations = corpus.get("review_confirmations", {})
    if reviewed and (
        not isinstance(confirmations, dict)
        or corpus.get("review_status") != "A_AND_C_CONFIRMED_UNCHANGED"
        or set(confirmations) != {"A", "C"}
        or any(
            not isinstance(item, dict)
            or item.get("status") != "CONFIRMED_UNCHANGED"
            or not isinstance(item.get("reference"), str)
            or not item["reference"].startswith("https://github.com/OriginProof-3web/OriginProof/")
            for item in confirmations.values()
        )
    ):
        raise ValueError("review confirmations missing or invalid")
    cases = []
    for case in corpus["cases"]:
        row = by_id[case["id"]]
        if (
            row["source_text_sha256"] != hashlib.sha256(case["text"].encode()).hexdigest()
            or row["split"] != case["split"]
            or row["proposed_label"] != case["label"]
        ):
            raise ValueError("self-review source, split or label mismatch")
        cases.append(
            {
                "id": case["id"],
                "source_group": case["source_group"],
                "proposed_split": case["split"],
                "proposed_label": case["label"],
                "text": case["text"],
                "expected_evidence": case["expected_evidence"],
                "d_proposed_basis": row["basis"],
                "flags": row["flags"],
                "a_review": confirmations["A"].copy()
                if reviewed
                else {"status": "PENDING", "reference": None, "notes": None},
                "c_review": confirmations["C"].copy()
                if reviewed
                else {"status": "PENDING", "reference": None, "notes": None},
                "planned_variants": [
                    {
                        "id": case["id"] + "-" + kind,
                        "kind": kind,
                        "source_group": case["source_group"],
                        "split": case["split"],
                        "asset_status": "SOURCE_TEXT_AVAILABLE"
                        if kind == "TEXT"
                        else "NOT_CREATED",
                        "conversion_evaluated": False,
                        "model_evaluated": False,
                    }
                    for kind in MODALITIES
                ],
            }
        )
    assets = None
    pack_root = corpus_path.parent / "selected_input_development_v1"
    if (pack_root / "manifest.json").exists():
        from .input_asset_pack import check_pack

        assets = check_pack(corpus_path, pack_root)
        manifest = json.loads((pack_root / "manifest.json").read_text())
        source_assets = {row["source_id"]: row for row in manifest["cases"]}
        for case in cases:
            if case["id"] not in source_assets:
                continue
            row = source_assets[case["id"]]
            for variant in case["planned_variants"]:
                if variant["kind"] == "DOCUMENT_IMAGE":
                    variant["asset_status"] = row["image_status"]
                    variant["asset_path"] = (
                        "selected_input_development_v1/" + row["image_asset"]["path"]
                        if row["image_asset"]
                        else None
                    )
    return {
        "version": "v5-d-input-review-0.3",
        "audio_scope": (
            "DEFERRED_FUTURE_EXTENSION; NOT_CURRENTLY_SUPPORTED; HISTORICAL_ASSETS_ONLY"
        ),
        "execution_flags_scope": "EXPORT_ASSET_PREPARATION_ONLY; TEXT_RUNS_SEPARATE",
        "generated_development_assets": assets,
        "date_kst": "2026-10-25" if reviewed else "2026-10-23",
        "source": "synthetic",
        "purpose": "Recorded A/C confirmations; export never approves or executes calls"
        if reviewed
        else "D preparation for A and C review; no human approval or evaluation execution",
        "decision": {
            "authority": "Representative decision, 2026-10-26; text and images only",
            "selected_inputs": list(MODALITIES),
            "priority": "TEXT_EVALUATION_FIRST; REMAINING_ORDER_PROPOSED"
            if reviewed
            else "UNDECIDED",
            "document_formats_pdf_inclusion": "DOCUMENT_IMAGES_ONLY; PDF_NOT_SELECTED"
            if reviewed
            else "UNDECIDED",
            "model": "gpt-6-luna",
            "budget": "ISSUE_92_TEXT_SCOPE; LOCAL_FUNDING_UNVERIFIED"
            if reviewed
            else "EXCLUDED_FROM_CURRENT_PREPARATION",
            "call_scope": "TEXT_DEVELOPMENT_24_PREPARED_DISABLED" if reviewed else "UNDECIDED",
            "approved_for_paid_calls": False,
        },
        "source_fixture_sha256": corpus_hash,
        "self_review_sha256": hashlib.sha256(self_review_path.read_bytes()).hexdigest(),
        "labels_human_reviewed": reviewed,
        "review_status": corpus["review_status"] if reviewed else "A_AND_C_REVIEW_PENDING",
        "similarity_caveat": corpus.get("similarity_caveat"),
        "source_cases": 60,
        "proposed_split": {"development": 24, "holdout": 36},
        "planned_variants": 60 * len(MODALITIES),
        "variant_count_is_not_independent_sources_or_evaluated_assets": True,
        "split_review_groups": review["split_review_groups"],
        "paid_calls": 0,
        "holdout_predictions": 0,
        "cases": cases,
    }


def render_markdown(packet: dict) -> str:
    reviewed = packet["labels_human_reviewed"]
    lines = [
        "# D 입력·평가 A/C 검토본 — " + packet["date_kst"],
        "",
        "2026-10-26 결정: 텍스트·이미지(문서)만 선정, "
        "음성은 보류(향후 확장)로 현재 지원에서 제외. gpt-6-luna 유지.",
        "텍스트 평가 우선, PDF 파일은 미선정입니다."
        if reviewed
        else "세부 형식·우선순위 미정입니다.",
        "개발24/최종36 제안은 A/C가 수정 없이 확인했습니다."
        if reviewed
        else "라벨·근거는 D 초안이며 A/C 검토 PENDING입니다.",
        "유료 정책은 별도이며 기본 비승인입니다. 이 생성기는 실제 호출·승인을 하지 않습니다.",
        "120은 두 형식 매핑 수이며 독립 원본/제작/변환/실제 평가 완료 수가 아닙니다.",
        "paid/model flag는 export 준비 범위입니다. 실제 텍스트 평가 이력은 별도 보고서입니다.",
        "텍스트 위치는 Unicode 코드 포인트 [start,end)이며 "
        "이미지 영역으로 복사하지 않습니다.",
        "아래 D 판단 근거·flags·분할 관계는 검토 전 제안 이력으로 보존합니다.",
        "",
    ]
    if reviewed:
        lines.extend(
            [
                "- A 확인: " + packet["cases"][0]["a_review"]["reference"],
                "- C 확인: " + packet["cases"][0]["c_review"]["reference"],
                "- H01/H11 문구 공유: 분할 유지. 최종 H11 결과 별도 표시(현재 예측 없음).",
                "- H08 추가 인용 권고는 미적용했습니다. 기존 라벨·원문·인용·분할을 보존합니다.",
                "- U05/U13/U15는 텍스트 사례이며 실제 OCR/STT 실패 수로 합산하지 않습니다.",
                "",
            ]
        )
    if packet.get("generated_development_assets"):
        assets = packet["generated_development_assets"]
        lines.extend(
            [
                f"개발 이미지 {assets['image_assets']}개, "
                "이미지 변환 평가0. 기존 녹음 대본은 보류(향후 확장) 자료로 보존합니다.",
                "[이미지/녹음 계획 manifest]"
                "(../../fixtures/synthetic/selected_input_development_v1/manifest.json)",
                "",
            ]
        )
    lines.extend(["## 분할 관계 기록", ""])
    for group in packet["split_review_groups"]:
        lines.append("- " + ", ".join(group["ids"]) + ": " + group["reason"])
    lines.extend(["", "## 사례별 검토", ""])
    for case in packet["cases"]:
        lines.extend(
            [
                "### "
                + case["id"]
                + " · "
                + case["proposed_split"]
                + " · "
                + case["proposed_label"],
                "",
                "> " + case["text"].replace("\n", "\n> "),
                "",
                "- D 판단 근거: " + case["d_proposed_basis"],
                "- 원래 flag: " + (", ".join(case["flags"]) or "없음"),
            ]
        )
        for quote in case["expected_evidence"]:
            lines.append(
                f"- 인용 [{quote['start_offset']},{quote['end_offset']}): {quote['quote']}"
            )
        if not case["expected_evidence"]:
            lines.append("- 기대 인용 없음")
        lines.extend([f"- A: {case['a_review']['status']} / C: {case['c_review']['status']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="compare generated proposal; never write"
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="explicitly replace generated exports after reviewing human notes",
    )
    args = parser.parse_args()
    if args.check and args.regenerate:
        parser.error("--check and --regenerate are mutually exclusive")
    root = Path(__file__).resolve().parents[4]
    fixtures = root / "fixtures/synthetic"
    packet = build_packet(
        fixtures / "phishing_sources_v1.json", fixtures / "phishing_sources_v1_review.json"
    )
    outputs = {
        fixtures / "v5_d_input_evaluation_review_v1.json": json.dumps(
            packet, ensure_ascii=False, indent=2
        )
        + "\n",
        root / "docs/qa/v5-d-input-evaluation-review-20261023.md": render_markdown(packet),
    }
    if not args.check and not args.regenerate and any(path.exists() for path in outputs):
        raise SystemExit("refusing to overwrite an existing proposal; preserve human notes")
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit("review proposal differs: " + str(path.relative_to(root)))
        else:
            path.write_text(content, encoding="utf-8")
    print(
        "A/C review export consistent: 60 sources, 24/36 split, "
        "120 planned variants; calls/predictions 0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
