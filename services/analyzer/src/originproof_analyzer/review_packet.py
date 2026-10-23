"""Export the existing synthetic corpus for A/C review; no provider or predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .phishing_evaluation import load_corpus

MODALITIES = ("TEXT", "DOCUMENT_IMAGE", "AUDIO")


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
                "a_review": {"status": "PENDING", "reference": None, "notes": None},
                "c_review": {"status": "PENDING", "reference": None, "notes": None},
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
    return {
        "version": "v5-d-input-review-0.1",
        "date_kst": "2026-10-23",
        "source": "synthetic",
        "purpose": "D preparation for A and C review; no human approval or evaluation execution",
        "decision": {
            "authority": "D user instruction in this chat, 2026-10-23",
            "selected_inputs": list(MODALITIES),
            "priority": "UNDECIDED",
            "document_formats_pdf_inclusion": "UNDECIDED",
            "audio_codecs": "UNDECIDED",
            "model": "gpt-6-luna",
            "budget": "EXCLUDED_FROM_CURRENT_PREPARATION",
            "call_scope": "UNDECIDED",
            "approved_for_paid_calls": False,
        },
        "source_fixture_sha256": corpus_hash,
        "self_review_sha256": hashlib.sha256(self_review_path.read_bytes()).hexdigest(),
        "labels_human_reviewed": False,
        "review_status": "A_AND_C_REVIEW_PENDING",
        "source_cases": 60,
        "proposed_split": {"development": 24, "holdout": 36},
        "planned_variants": 180,
        "variant_count_is_not_independent_sources_or_evaluated_assets": True,
        "split_review_groups": review["split_review_groups"],
        "paid_calls": 0,
        "holdout_predictions": 0,
        "cases": cases,
    }


def render_markdown(packet: dict) -> str:
    lines = [
        "# D 입력·평가 A/C 검토본 — 2026-10-23",
        "",
        "텍스트·이미지(문서)·음성 선택 완료. 모델 "
        "gpt-6-luna. 우선순위·PDF 포함·음성 코덱은 미정입니다.",
        "예산은 이번 준비에서 제외하고 호출 범위도 미정으로 유지합니다. 유료 호출 승인이 아닙니다.",
        "",
        "기존 합성 원본60개·개발24/보류36 제안을 재사용합니다. 아래 "
        "라벨·근거는 D 초안이며 A와 C의 검토는 PENDING입니다.",
        "180개는 원본별 세 형식의 제작 계획 수입니다. 독립 "
        "원본180개나 실제 이미지/음성 제작·변환·평가 완료 수가 아닙니다.",
        "텍스트 위치는 Unicode 코드 포인트 "
        "[start,end)이며 이미지 영역·음성 시간의 정답으로 자동 복사하지 않습니다.",
        "",
        "A: 표현·문맥·입력 UX/인식 부족 안내를 검토합니다. "
        "C: 계약·근거 위치·오류/보관 및 분할 누출을 검토합니다.",
        "각자 JSON의 a_review/c_review에 실제 검토 "
        "reference와 의견을 남기거나 PR에 사례 ID로 답해 주세요.",
        "승인과 수정 요청을 구분하고 라벨 변경은 제안으로 남겨 D가 원본 변경·재검사 후 반영합니다.",
        "이 생성기는 제안본을 재생성합니다. 사람 의견은 원본 "
        "JSON에 덮어쓰지 말고 별도 검토 사본/PR 댓글로 보존하세요.",
        "",
        "## 먼저 검토할 분할 관계",
        "",
    ]
    for group in packet["split_review_groups"]:
        lines.append("- " + ", ".join(group["ids"]) + ": " + group["reason"])
    lines.extend(["", "## 사례별 제안", ""])
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
                "- 추가 검토: " + (", ".join(case["flags"]) or "별도 flag 없음; 사람 검토 필요"),
            ]
        )
        for quote in case["expected_evidence"]:
            lines.append(
                f"- 제안 인용 [{quote['start_offset']},{quote['end_offset']}): {quote['quote']}"
            )
        if not case["expected_evidence"]:
            lines.append("- 제안 인용 없음: 근거 부재와 NO_CLEAR_INDICATORS/UNDETERMINED 구분 검토")
        lines.extend(["- A: PENDING / C: PENDING", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="compare generated proposal; never write"
    )
    args = parser.parse_args()
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
    if not args.check and any(path.exists() for path in outputs):
        raise SystemExit("refusing to overwrite an existing proposal; preserve human notes")
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit("review proposal differs: " + str(path.relative_to(root)))
        else:
            path.write_text(content, encoding="utf-8")
    print(
        "A/C proposal consistent: 60 sources, 24/36 split, "
        "180 planned variants; calls/predictions 0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
