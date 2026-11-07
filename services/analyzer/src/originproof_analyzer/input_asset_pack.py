"""Offline development image assets and recording drafts, never OCR/STT/model evaluation."""

# AUDIO/WAV/STT: deferred for future extension; not a currently supported input.
# Preserve historical validation and assets; current inputs are TEXT/DOCUMENT_IMAGE.

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
import wave
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL import __version__ as pillow_version

from .audio_inputs import inspect_pcm_wav
from .inputs import SemanticInput
from .phishing_evaluation import load_corpus

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CORPUS = ROOT / "fixtures/synthetic/phishing_sources_v1.json"
DEFAULT_PACK = DEFAULT_CORPUS.parent / "selected_input_development_v1"
DEFAULT_SPEECH = DEFAULT_CORPUS.parent / "local_tts_development_preview_v1"
# A/C PR94 and issue92: these placeholders are text controls, not actual media failures.
TEXT_ONLY_IDS = frozenset({"DP-U05", "DP-U13", "DP-U15"})


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _development(path):
    corpus = load_corpus(path)
    if corpus.get("labels_human_reviewed") is not True or corpus.get("input_selection") != "TEXT":
        raise ValueError("reviewed text corpus required")
    cases = [case for case in corpus["cases"] if case["split"] == "development"]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", case["id"]) for case in cases):
        raise ValueError("unsafe case id")
    return cases


def _row(case):
    text = case["text"]
    flags = []
    for pattern, name in [
        (r"https?://", "URL_PRONUNCIATION_UNDECIDED"),
        (r"[0-9]", "NUMBER_TRANSCRIPTION_CONVENTION_UNDECIDED"),
        (r"[A-Za-z]", "LATIN_TOKEN_PRONUNCIATION_REVIEW"),
        (r"\[", "STAGE_DIRECTION_REQUIRES_ADAPTATION"),
    ]:
        if re.search(pattern, text):
            flags.append(name)
    text_only = case["id"] in TEXT_ONLY_IDS
    spoken = bool(re.search(r"[A-Za-z0-9가-힣]", text))
    return {
        "source_id": case["id"],
        "source_group": case["source_group"],
        "split": "development",
        "label_from_text": case["label"],
        "reference_text": text,
        "source_expected_evidence": case["expected_evidence"],
        "modality_review": "PENDING; TEXT_REVIEW_DOES_NOT_APPROVE_IMAGE_OR_SPEECH_QUALITY",
        "image_status": "EXCLUDED_AGREED_TEXT_ONLY" if text_only else "CREATED_NOT_EVALUATED",
        "recording": {
            "status": "EXCLUDED_AGREED_TEXT_ONLY"
            if text_only
            else ("NO_SPOKEN_WORDS_SCRIPT_NOT_READY" if not spoken else "DRAFT_AUDIO_NOT_RECORDED"),
            "candidate_script": text if spoken and not text_only else None,
            "review_flags": flags,
            "audio_asset": None,
            "reference_transcript": None,
            "word_or_evidence_timestamps": None,
            "human_reviewed": False,
        },
        "image_conversion_evaluated": False,
        "speech_conversion_evaluated": False,
    }


def _guide(rows):
    lines = [
        "# 합성 음성 녹음 준비표 — 아직 녹음/전사 정답 없음",
        "",
        "개발용 원본만 재사용합니다. 새 독립 원본이나 실제 STT 평가 결과가 아닙니다.",
        "아래 대본은 후보입니다. URL·숫자·영문 발음, 대괄호 지시문은 검토 후 확정합니다.",
        "원문을 임의 수정하거나 지시문을 실제 발화로 읽어 정답을 만들지 마세요.",
        "녹음 뒤 들리는 말로 정답 전사를 검토합니다. "
        "텍스트 위치를 음성 시간으로 복사하지 않습니다.",
        "현재 내부 검사 지원은 정수 PCM WAV·20MiB/300초/2채널 이내입니다.",
        "전사 모델·MP3/M4A 지원은 미정입니다. 개인 대화/실기관 자료 대신 합성 대본만 사용합니다.",
        "유료 TTS/STT 호출·자동 녹음·평가셋 동결을 수행하지 않습니다.",
        "",
    ]
    for row in rows:
        audio = row["recording"]
        lines.extend(
            [
                "## " + row["source_id"],
                "",
                "- 상태: " + audio["status"],
                "- 검토: "
                + (", ".join(audio["review_flags"]) or "별도 발음 flag 없음; 실제 낭독 검토 필요"),
                "- 최종 전사·시간 정답: 미작성",
                "",
                "> " + audio["candidate_script"]
                if audio["candidate_script"]
                else "낭독 대본 미생성.",
                "",
            ]
        )
    return "\n".join(lines)


def generate_pack(corpus_path: Path, output: Path, font_path: Path, *, font_index=0):
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to overwrite existing assets or review notes")
    cases = _development(corpus_path)
    font = ImageFont.truetype(
        str(font_path), 28, index=font_index, layout_engine=ImageFont.Layout.BASIC
    )
    missing = font.getmask("\U0010ffff")
    notdef = (missing.size, bytes(missing))
    for char in {char for c in cases for char in c["text"] if not char.isspace()}:
        mask = font.getmask(char)
        if not bytes(mask) or (mask.size, bytes(mask)) == notdef:
            raise ValueError("font does not cover source characters")
    rendered, rows = {}, []
    for case in cases:
        row = _row(case)
        row["image_asset"] = None
        if case["id"] not in TEXT_ONLY_IDS:
            text = case["text"]
            if "\n" in text or "\r" in text:
                raise ValueError("single-line renderer requires explicit line-break design")
            left, top, right, bottom = font.getbbox(text)
            size = (max(128, right - left + 48), max(80, bottom - top + 48))
            if size[0] > 4096 or size[1] > 512:
                raise ValueError("render size limit")
            image = Image.new("RGB", size, "white")
            ImageDraw.Draw(image).text((24 - left, 24 - top), text, font=font, fill="black")
            stream = BytesIO()
            image.save(stream, format="PNG")
            data = stream.getvalue()
            SemanticInput(
                image_base64=base64.b64encode(data).decode(), image_media_type="image/png"
            )
            name = f"images/{case['id']}.png"
            rendered[name] = data
            row["image_asset"] = {
                "path": name,
                "sha256": _sha(data),
                "width": size[0],
                "height": size[1],
            }
        rows.append(row)
    guide = _guide(rows).encode()
    manifest = {
        "version": "selected-input-development-0.1",
        "source": "synthetic",
        "purpose": "Rendered text references and recording drafts; no media accuracy measured",
        "source_fixture_sha256": _sha(corpus_path.read_bytes()),
        "font": {
            "file_name": font_path.name,
            "sha256": _sha(font_path.read_bytes()),
            "index": font_index,
            "size": 28,
            "family": font.getname()[0],
            "renderer": "Pillow BASIC " + pillow_version,
            "redistributed": False,
            "source_glyph_coverage_checked": True,
        },
        "image_content": "SOURCE_TEXT_ONLY; NO_LABEL_OR_ANSWER_METADATA",
        "audio_recordings": 0,
        "paid_calls": 0,
        "holdout_assets_created": 0,
        "image_pixel_region_annotations": None,
        "recording_guide_sha256": _sha(guide),
        "cases": rows,
    }
    output.mkdir(parents=True)
    (output / "images").mkdir()
    for name, data in rendered.items():
        (output / name).write_bytes(data)
    (output / "recording_plan.md").write_bytes(guide)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def check_pack(corpus_path: Path = DEFAULT_CORPUS, root: Path = DEFAULT_PACK):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("pack symlink")
    manifest = json.loads((root / "manifest.json").read_text())
    if (
        manifest.get("version") != "selected-input-development-0.1"
        or manifest.get("source") != "synthetic"
        or manifest.get("source_fixture_sha256") != _sha(corpus_path.read_bytes())
        or any(
            manifest.get(k) != 0
            for k in ("audio_recordings", "paid_calls", "holdout_assets_created")
        )
        or manifest.get("image_pixel_region_annotations") is not None
        or manifest.get("image_content") != "SOURCE_TEXT_ONLY; NO_LABEL_OR_ANSWER_METADATA"
    ):
        raise ValueError("pack identity or unmeasured scope")
    if any(
        type(manifest.get(k)) is not int
        for k in ("audio_recordings", "paid_calls", "holdout_assets_created")
    ):
        raise ValueError("scope count types")
    font = manifest.get("font")
    if (
        not isinstance(font, dict)
        or not isinstance(font.get("sha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", font["sha256"])
        or font.get("redistributed") is not False
        or font.get("source_glyph_coverage_checked") is not True
        or type(font.get("index")) is not int
        or font["index"] < 0
        or font.get("size") != 28
        or not isinstance(font.get("family"), str)
        or not font["family"]
        or not isinstance(font.get("file_name"), str)
        or Path(font["file_name"]).name != font["file_name"]
    ):
        raise ValueError("font provenance")
    cases, rows = _development(corpus_path), manifest["cases"]
    if [r["source_id"] for r in rows] != [c["id"] for c in cases]:
        raise ValueError("source row identity")
    expected_files = {"manifest.json", "recording_plan.md"}
    images, scripts = 0, 0
    for case, row in zip(cases, rows, strict=True):
        if {k: v for k, v in row.items() if k != "image_asset"} != _row(case):
            raise ValueError("reference or review scope changed")
        asset = row["image_asset"]
        if case["id"] in TEXT_ONLY_IDS:
            if asset is not None:
                raise ValueError("text-only placeholder is not an image evaluation")
        else:
            name = f"images/{case['id']}.png"
            if (
                not isinstance(asset, dict)
                or set(asset) != {"path", "sha256", "width", "height"}
                or asset.get("path") != name
            ):
                raise ValueError("image path")
            data = (root / name).read_bytes()
            if _sha(data) != asset.get("sha256"):
                raise ValueError("image integrity")
            SemanticInput(
                image_base64=base64.b64encode(data).decode(), image_media_type="image/png"
            )
            with Image.open(BytesIO(data)) as image:
                if image.size != (asset.get("width"), asset.get("height")) or image.info:
                    raise ValueError("image dimensions or hidden metadata")
            expected_files.add(name)
            images += 1
        scripts += row["recording"]["candidate_script"] is not None
    guide = (root / "recording_plan.md").read_bytes()
    if guide != _guide(rows).encode() or _sha(guide) != manifest["recording_guide_sha256"]:
        raise ValueError("recording guide changed")
    if {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} != expected_files:
        raise ValueError("unlisted or missing files")
    return {
        "status": "OFFLINE_ASSET_CONSISTENCY_PASS",
        "source_rows": len(rows),
        "image_assets": images,
        "recording_script_drafts": scripts,
        "audio_recordings": 0,
        "actual_conversion_evaluations": 0,
        "paid_calls": 0,
        "holdout_assets_created": 0,
        "pixel_or_audio_time_annotations": "NOT_CREATED",
    }


def _speech_rows(corpus_path):
    return [
        case
        for case in _development(corpus_path)
        if _row(case)["recording"]["candidate_script"] is not None
        and not _row(case)["recording"]["review_flags"]
    ]


def generate_speech_previews(corpus_path: Path, output: Path, voice: str):
    """Explicit macOS local fixture generation only; no model API or audio playback."""
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to overwrite speech assets")
    if sys.platform != "darwin" or not Path("/usr/bin/say").is_file():
        raise ValueError("native local TTS requires macOS; no download or paid fallback")
    if not isinstance(voice, str) or not voice.strip():
        raise ValueError("explicit installed local voice required")
    prepared = []
    with tempfile.TemporaryDirectory(prefix="originproof-tts-") as temporary:
        work = Path(temporary)
        for case in _speech_rows(corpus_path):
            text, native = work / "script.txt", work / "native.wav"
            text.write_text(case["text"])
            subprocess.run(
                [
                    "/usr/bin/say",
                    "-v",
                    voice,
                    "-r",
                    "180",
                    "-o",
                    str(native),
                    "--file-format=WAVE",
                    "--data-format=LEI16@16000",
                    "--channels=1",
                    "-f",
                    str(text),
                ],
                check=True,
                capture_output=True,
                timeout=45,
            )
            with wave.open(str(native), "rb") as source:
                params = source.getparams()
                frames = source.readframes(source.getnframes())
            if (
                params.comptype != "NONE"
                or params.nframes < 1
                or len(frames) != (params.nframes * params.nchannels * params.sampwidth)
            ):
                raise ValueError("native TTS returned no complete PCM frames")
            stream = BytesIO()
            with wave.open(stream, "wb") as target:
                target.setparams(params)
                target.writeframes(frames)
            data = stream.getvalue()
            info = inspect_pcm_wav(data, "audio/wav")
            with wave.open(BytesIO(data), "rb") as check:
                if check.readframes(check.getnframes()) != frames:
                    raise ValueError("PCM changed during header canonicalization")
            prepared.append((case, data, asdict(info)))
    output.mkdir(parents=True)
    rows = []
    for case, data, info in prepared:
        name = case["id"] + ".wav"
        (output / name).write_bytes(data)
        rows.append(
            {
                "source_id": case["id"],
                "source_group": case["source_group"],
                "split": "development",
                "label_from_text": case["label"],
                "candidate_script": case["text"],
                "audio_path": name,
                "sha256": _sha(data),
                "pcm_info": info,
                "reference_transcript": None,
                "word_or_evidence_timestamps": None,
                "human_reviewed": False,
                "stt_evaluated": False,
            }
        )
    manifest = {
        "version": "local-tts-development-preview-0.1",
        "source": "synthetic",
        "purpose": "Local unreviewed TTS drafts; not an STT model, "
        "human recording or final evaluation set",
        "source_fixture_sha256": _sha(corpus_path.read_bytes()),
        "generator": {
            "engine": "macOS /usr/bin/say",
            "voice": voice,
            "rate_words_per_minute": 180,
            "platform_version": platform.mac_ver()[0],
            "say_binary_sha256": _sha(Path("/usr/bin/say").read_bytes()),
            "canonicalization": "stdlib wave header only; PCM frames preserved",
            "network_api_calls": 0,
            "product_stt_model_selected": False,
        },
        "speech_assets": len(rows),
        "human_verified_transcripts": 0,
        "speech_evaluations": 0,
        "paid_api_calls": 0,
        "holdout_assets": 0,
        "cases": rows,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def check_speech_previews(corpus_path: Path = DEFAULT_CORPUS, root: Path = DEFAULT_SPEECH):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("speech pack symlink")
    manifest = json.loads((root / "manifest.json").read_text())
    if (
        manifest.get("version") != "local-tts-development-preview-0.1"
        or manifest.get("source") != "synthetic"
        or manifest.get("source_fixture_sha256") != _sha(corpus_path.read_bytes())
        or any(
            type(manifest.get(k)) is not int or manifest[k] != 0
            for k in (
                "human_verified_transcripts",
                "speech_evaluations",
                "paid_api_calls",
                "holdout_assets",
            )
        )
    ):
        raise ValueError("speech identity or unreviewed scope")
    generator = manifest.get("generator", {})
    if (
        generator.get("engine") != "macOS /usr/bin/say"
        or not isinstance(generator.get("voice"), str)
        or not generator["voice"]
        or generator.get("rate_words_per_minute") != 180
        or generator.get("network_api_calls") != 0
        or generator.get("product_stt_model_selected") is not False
    ):
        raise ValueError("local speech generator scope")
    source, rows = _speech_rows(corpus_path), manifest["cases"]
    if [r["source_id"] for r in rows] != [c["id"] for c in source]:
        raise ValueError("speech source identity")
    if manifest["speech_assets"] != len(rows):
        raise ValueError("speech count")
    expected_files = {"manifest.json"}
    for case, row in zip(source, rows, strict=True):
        name = case["id"] + ".wav"
        if (
            row["audio_path"] != name
            or row["candidate_script"] != case["text"]
            or row["source_group"] != case["source_group"]
            or row["split"] != "development"
            or row["label_from_text"] != case["label"]
            or row["human_reviewed"] is not False
            or row["stt_evaluated"] is not False
            or row["reference_transcript"] is not None
            or row["word_or_evidence_timestamps"] is not None
        ):
            raise ValueError("speech reference or human-review claim")
        data = (root / name).read_bytes()
        if (
            _sha(data) != row["sha256"]
            or asdict(inspect_pcm_wav(data, "audio/wav")) != row["pcm_info"]
        ):
            raise ValueError("speech PCM integrity")
        expected_files.add(name)
    if {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} != expected_files:
        raise ValueError("unlisted or missing speech files")
    return {
        "status": "OFFLINE_LOCAL_TTS_CONSISTENCY_PASS",
        "local_tts_drafts": len(rows),
        "human_verified_transcripts": 0,
        "actual_stt_evaluations": 0,
        "paid_api_calls": 0,
        "holdout_assets": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--font", type=Path)
    parser.add_argument("--speech", action="store_true")
    parser.add_argument("--voice")
    args = parser.parse_args()
    root = args.root or (DEFAULT_SPEECH if args.speech else DEFAULT_PACK)
    if args.generate:
        if args.speech:
            if not args.voice:
                parser.error("--generate --speech requires an explicit installed --voice")
            generate_speech_previews(args.corpus, root, args.voice)
        else:
            if args.font is None:
                parser.error("--generate requires an explicit local font")
            generate_pack(args.corpus, root, args.font)
    print(
        json.dumps(
            check_speech_previews(args.corpus, root)
            if args.speech
            else check_pack(args.corpus, root)
        )
    )


if __name__ == "__main__":
    main()
