"""Review export integrity and non-execution boundaries, not OCR/STT/model quality."""

import hashlib
import json
import socket
from pathlib import Path

import pytest
from originproof_analyzer.review_packet import MODALITIES, build_packet, main, render_markdown

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "fixtures/synthetic/phishing_sources_v1.json"
SELF_REVIEW = ROOT / "fixtures/synthetic/phishing_sources_v1_review.json"


def test_offline_packet_preserves_sources_splits_and_recorded_reviews(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("review export must not call a provider")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    before = CORPUS.read_bytes(), SELF_REVIEW.read_bytes()
    packet = build_packet(CORPUS, SELF_REVIEW)
    assert packet["source_fixture_sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert packet["decision"]["selected_inputs"] == list(MODALITIES)
    assert packet["decision"]["approved_for_paid_calls"] is False
    assert packet["decision"]["call_scope"] == "TEXT_DEVELOPMENT_24_PREPARED_DISABLED"
    assert packet["labels_human_reviewed"] is True
    assert packet["paid_calls"] == packet["holdout_predictions"] == 0
    assert len(packet["cases"]) == 60
    assert sum(c["proposed_split"] == "development" for c in packet["cases"]) == 24
    variants = [v for c in packet["cases"] for v in c["planned_variants"]]
    assert len(variants) == len({v["id"] for v in variants}) == 180
    originals = json.loads(before[0])["cases"]
    for original, case in zip(originals, packet["cases"], strict=True):
        assert case["text"] == original["text"]
        assert case["proposed_label"] == original["label"]
        assert case["expected_evidence"] == original["expected_evidence"]
        assert case["a_review"]["status"] == case["c_review"]["status"] == "CONFIRMED_UNCHANGED"
        assert {v["source_group"] for v in case["planned_variants"]} == {original["source_group"]}
        assert {v["split"] for v in case["planned_variants"]} == {original["split"]}
        assert all(
            not v["conversion_evaluated"] and not v["model_evaluated"]
            for v in case["planned_variants"]
        )
    assert (CORPUS.read_bytes(), SELF_REVIEW.read_bytes()) == before
    assert "DP-H05" in render_markdown(packet) and packet["split_review_groups"]


@pytest.mark.parametrize("change", ["corpus_hash", "text_hash", "split", "label", "duplicate"])
def test_mismatched_self_review_is_rejected(tmp_path, change):
    review = json.loads(SELF_REVIEW.read_text())
    if change == "corpus_hash":
        review["source_fixture_sha256"] = "0" * 64
    elif change == "text_hash":
        review["cases"][0]["source_text_sha256"] = "0" * 64
    elif change == "split":
        review["cases"][0]["split"] = "holdout"
    elif change == "label":
        review["cases"][0]["proposed_label"] = "UNDETERMINED"
    else:
        review["cases"][-1] = review["cases"][0]
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review))
    with pytest.raises(ValueError):
        build_packet(CORPUS, path)


def test_checked_in_export_matches_generator_and_cannot_overwrite_notes(monkeypatch):
    monkeypatch.setattr("sys.argv", ["review_packet", "--check"])
    assert main() == 0
    monkeypatch.setattr("sys.argv", ["review_packet"])
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        main()


@pytest.mark.parametrize("change", ["missing", "role", "status", "reference", "type"])
def test_review_flag_without_valid_recorded_confirmations_is_rejected(tmp_path, change):
    corpus = json.loads(CORPUS.read_text())
    if change == "missing":
        corpus.pop("review_confirmations")
    elif change == "role":
        corpus["review_confirmations"].pop("A")
    elif change == "status":
        corpus["review_confirmations"]["A"]["status"] = "PENDING"
    elif change == "reference":
        corpus["review_confirmations"]["C"]["reference"] = ""
    else:
        corpus["review_confirmations"] = None
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(corpus))
    review = json.loads(SELF_REVIEW.read_text())
    review["source_fixture_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="review confirmations"):
        build_packet(path, review_path)
