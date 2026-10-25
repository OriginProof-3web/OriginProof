"""Committed rendered references/draft scripts, not OCR/STT/LLM accuracy."""

import json
import shutil
from pathlib import Path

import pytest
from originproof_analyzer.input_asset_pack import (
    DEFAULT_CORPUS,
    DEFAULT_PACK,
    check_pack,
    generate_pack,
)


def test_pack_reuses_only_development_and_keeps_audio_reference_uninvented():
    result = check_pack()
    assert (result["source_rows"], result["image_assets"], result["recording_script_drafts"]) == (
        24,
        23,
        22,
    )
    assert result["audio_recordings"] == result["actual_conversion_evaluations"] == 0
    corpus = json.loads(DEFAULT_CORPUS.read_text())
    expected = [c for c in corpus["cases"] if c["split"] == "development"]
    rows = json.loads((DEFAULT_PACK / "manifest.json").read_text())["cases"]
    for original, row in zip(expected, rows, strict=True):
        assert row["reference_text"] == original["text"]
        assert row["source_expected_evidence"] == original["expected_evidence"]
        assert row["source_group"] == original["source_group"]
        assert row["label_from_text"] == original["label"]
        assert row["recording"]["audio_asset"] is None
        assert row["recording"]["reference_transcript"] is None
        assert row["recording"]["word_or_evidence_timestamps"] is None
        assert row["recording"]["human_reviewed"] is False
    by_id = {r["source_id"]: r for r in rows}
    assert by_id["DP-U05"]["image_asset"] is None
    assert by_id["DP-U05"]["recording"]["candidate_script"] is None
    assert by_id["DP-U03"]["recording"]["candidate_script"] is None
    assert "URL_PRONUNCIATION_UNDECIDED" in by_id["DP-C02"]["recording"]["review_flags"]
    assert "STAGE_DIRECTION_REQUIRES_ADAPTATION" in by_id["DP-U01"]["recording"]["review_flags"]
    assert (
        "NUMBER_TRANSCRIPTION_CONVENTION_UNDECIDED" in by_id["DP-U02"]["recording"]["review_flags"]
    )


@pytest.mark.parametrize(
    "change",
    [
        "corpus",
        "reference",
        "label",
        "split",
        "review",
        "audio",
        "timestamps",
        "image_hash",
        "traversal",
        "missing",
        "extra",
        "guide",
        "symlink",
        "text_only",
        "font",
        "paid",
        "bool_count",
    ],
)
def test_pack_tampering_or_fake_execution_claims_are_rejected(tmp_path, change):
    pack = tmp_path / "pack"
    shutil.copytree(DEFAULT_PACK, pack)
    p = pack / "manifest.json"
    value = json.loads(p.read_text())
    row = value["cases"][0]
    asset = pack / row["image_asset"]["path"]
    if change == "corpus":
        value["source_fixture_sha256"] = "0" * 64
    elif change in {"reference", "label", "split"}:
        row[
            {"reference": "reference_text", "label": "label_from_text", "split": "split"}[change]
        ] = "changed"
    elif change == "review":
        row["modality_review"] = "APPROVED"
    elif change == "audio":
        row["recording"]["audio_asset"] = "invented.wav"
    elif change == "timestamps":
        row["recording"]["word_or_evidence_timestamps"] = [[0, 1000]]
    elif change == "image_hash":
        asset.write_bytes(asset.read_bytes() + b"tampered")
    elif change == "traversal":
        row["image_asset"]["path"] = "../outside.png"
    elif change == "missing":
        asset.unlink()
    elif change == "extra":
        (pack / "unexpected.txt").write_text("not listed")
    elif change == "guide":
        (pack / "recording_plan.md").write_text("invented transcript")
    elif change == "symlink":
        asset.unlink()
        asset.symlink_to(DEFAULT_PACK / row["image_asset"]["path"])
    elif change == "text_only":
        next(r for r in value["cases"] if r["source_id"] == "DP-U05")["image_asset"] = row[
            "image_asset"
        ]
    elif change == "font":
        value["font"]["redistributed"] = True
    elif change == "paid":
        value["paid_calls"] = 1
    else:
        value["paid_calls"] = False
    p.write_text(json.dumps(value))
    with pytest.raises((ValueError, OSError)):
        check_pack(DEFAULT_CORPUS, pack)


def test_generator_never_overwrites_assets_or_human_recording_notes(tmp_path):
    pack = tmp_path / "existing"
    pack.mkdir()
    notes = pack / "review.md"
    notes.write_text("preserve my review")
    with pytest.raises(ValueError, match="overwrite"):
        generate_pack(DEFAULT_CORPUS, pack, Path("missing-font-do-not-load.ttf"))
    assert notes.read_text() == "preserve my review"
