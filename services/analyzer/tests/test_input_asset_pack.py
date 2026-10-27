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


def test_local_speech_is_real_pcm_but_never_an_approved_transcription():
    from originproof_analyzer.input_asset_pack import DEFAULT_SPEECH, check_speech_previews

    result = check_speech_previews()
    assert result["local_tts_drafts"] == 13
    assert result["human_verified_transcripts"] == result["actual_stt_evaluations"] == 0
    rows = json.loads((DEFAULT_SPEECH / "manifest.json").read_text())["cases"]
    assert {r["label_from_text"] for r in rows} == {
        "HIGH",
        "CAUTION",
        "NO_CLEAR_INDICATORS",
        "UNDETERMINED",
    }
    assert all(r["pcm_info"]["duration_ms"] > 0 for r in rows)
    assert all(r["pcm_info"]["sample_rate"] == 16000 for r in rows)
    assert all(r["reference_transcript"] is None for r in rows)


@pytest.mark.parametrize(
    "change",
    [
        "transcript",
        "timestamps",
        "human",
        "stt",
        "empty_frames",
        "path",
        "script",
        "symlink",
        "product_model",
        "extra",
    ],
)
def test_speech_drafts_reject_fabricated_review_or_tampered_pcm(tmp_path, change):
    import hashlib

    from originproof_analyzer.errors import AnalyzerError
    from originproof_analyzer.input_asset_pack import DEFAULT_SPEECH, check_speech_previews

    pack = tmp_path / "speech"
    shutil.copytree(DEFAULT_SPEECH, pack)
    manifest = pack / "manifest.json"
    value = json.loads(manifest.read_text())
    row = value["cases"][0]
    path = pack / row["audio_path"]
    if change == "transcript":
        row["reference_transcript"] = "invented truth"
    elif change == "timestamps":
        row["word_or_evidence_timestamps"] = [[0, 100]]
    elif change == "human":
        row["human_reviewed"] = True
    elif change == "stt":
        row["stt_evaluated"] = True
    elif change == "path":
        row["audio_path"] = "../outside.wav"
    elif change == "script":
        row["candidate_script"] = "modified words"
    elif change == "product_model":
        value["generator"]["product_stt_model_selected"] = True
    elif change == "extra":
        (pack / "unexpected.wav").write_bytes(b"fake")
    elif change == "symlink":
        path.unlink()
        path.symlink_to(DEFAULT_SPEECH / row["audio_path"])
    else:
        path.write_bytes(b"RIFF" + b"\0" * 40)
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(value))
    with pytest.raises((ValueError, OSError, AnalyzerError)):
        check_speech_previews(DEFAULT_CORPUS, pack)


def test_local_speech_generator_has_no_download_or_non_native_fallback(tmp_path, monkeypatch):
    import originproof_analyzer.input_asset_pack as module

    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: pytest.fail("no native call"))
    with pytest.raises(ValueError, match="requires macOS"):
        module.generate_speech_previews(DEFAULT_CORPUS, tmp_path / "no-speech", "Yuna")
    pack = tmp_path / "preserve"
    pack.mkdir()
    with pytest.raises(ValueError, match="overwrite"):
        module.generate_speech_previews(DEFAULT_CORPUS, pack, "Yuna")
