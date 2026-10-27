"""Committed media bytes and offline recipes; not recognition quality or human-labelled data."""

import json
import shutil
import socket

import pytest
from originproof_analyzer.media_fixtures import DEFAULT_ROOT, check, generate


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("fixture QA cannot access network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")  # Export/check still uses explicit mock only.


async def test_all_committed_bytes_and_twelve_failure_replays_without_quality_claims():
    report = await check(DEFAULT_ROOT)
    assert report["status"] == "OFFLINE_MEDIA_CONTRACT_PASS"
    assert len(report["media_cases"]) == 24 and len(report["failure_replays"]) == 12
    assert report["processor_calls"] == report["paid_calls"] == report["holdout_predictions"] == 0
    assert report["semantic_evaluation"] == "NOT_RUN"
    assert all(c["passed"] for c in report["media_cases"] + report["failure_replays"])
    manifest = json.loads((DEFAULT_ROOT / "manifest.json").read_text())
    assert manifest["audio_has_speech"] is False
    assert {c["source_group"] for c in manifest["cases"]} == {
        "D-MEDIA-DOCUMENT-01",
        "D-MEDIA-SIGNAL-01",
    }
    for condition in ["blurred", "tiny", "low_contrast", "silence", "non_speech_noise"]:
        row = next(c for c in manifest["cases"] if c["condition"] == condition)
        assert row["expected_error"] is None and not row["model_evaluated"]


async def test_fresh_generated_version_is_checkable_and_never_overwrites(tmp_path):
    root = tmp_path / "new-fixtures"
    generate(root)
    assert (await check(root))["status"] == "OFFLINE_MEDIA_CONTRACT_PASS"
    original = (root / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        generate(root)
    assert (root / "manifest.json").read_bytes() == original


@pytest.mark.parametrize(
    "change", ["bytes", "traversal", "symlink", "duplicate", "scope", "unlisted", "missing"]
)
async def test_tampered_unsafe_or_unaccounted_fixture_fails_closed(tmp_path, change):
    root = tmp_path / "fixtures"
    shutil.copytree(DEFAULT_ROOT, root)
    path = root / "manifest.json"
    data = json.loads(path.read_text())
    if change == "bytes":
        (root / "clear.png").write_bytes(b"TAMPERED")
    elif change == "traversal":
        data["cases"][0]["file"] = "../outside.png"
    elif change == "symlink":
        (root / "clear.png").unlink()
        (root / "clear.png").symlink_to(DEFAULT_ROOT / "clear.png")
    elif change == "duplicate":
        data["cases"][-1]["id"] = data["cases"][0]["id"]
    elif change == "scope":
        data["cases"][0]["model_evaluated"] = True
    elif change == "unlisted":
        (root / "extra.bin").write_bytes(b"UNLISTED")
    else:
        data["failure_replays"].pop()
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        await check(root)
