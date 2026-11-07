"""Build/check synthetic byte fixtures and failure replays offline, never model accuracy."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import math
import random
import struct
import sys
import wave
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from PIL import __version__ as pillow_version
from pydantic import ValidationError

from .audio_inputs import MAX_AUDIO_BYTES, inspect_pcm_wav
from .converted_inputs import analyze_conversion
from .errors import AnalyzerError
from .inputs import SemanticInput
from .phishing import PhishingAnalyzer
from .providers import MockLLMProvider

DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "fixtures/synthetic/media_safety_v1"
NOTICE = "SYNTHETIC - NOT OFFICIAL\nMock Notice 001\nCheck the official channel."


def _encoded(image, format="PNG", **options):
    output = BytesIO()
    image.save(output, format=format, **options)
    return output.getvalue()


def _pcm(signal="tone", channels=1):
    rng, frames = random.Random(20261023), []
    for sample in range(800):
        value = (
            int(6000 * math.sin(2 * math.pi * 440 * sample / 8000))
            if signal == "tone"
            else rng.randint(-6000, 6000)
            if signal == "noise"
            else (32767 if sample % 2 else -32768)
            if signal == "clipped"
            else 0
        )
        frames.extend([value] * channels)
    output = BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setparams((channels, 2, 8000, 800, "NONE", "not compressed"))
        writer.writeframes(struct.pack("<" + "h" * len(frames), *frames))
    return output.getvalue()


def _riff_size(data):
    value = bytearray(data)
    struct.pack_into("<I", value, 4, len(value) - 8)
    return bytes(value)


def generate(root: Path) -> None:
    """Create a new fixture version only; never overwrite assets or reviewer notes."""
    if root.exists() or root.is_symlink():
        raise ValueError("fixture directory already exists")
    image = Image.new("RGB", (640, 240), "white")
    ImageDraw.Draw(image).multiline_text((24, 40), NOTICE, fill="black", font_size=24)
    plain = _encoded(image)
    low = Image.new("RGB", image.size, (245, 245, 245))
    ImageDraw.Draw(low).multiline_text((24, 40), NOTICE, fill=(235, 235, 235), font_size=24)
    orientation = Image.Exif()
    orientation[274] = 6
    animated = _encoded(image, save_all=True, append_images=[low], duration=100)
    images = [
        ("clear.png", plain, "image/png", None, "clear"),
        ("notice.jpg", _encoded(image, "JPEG"), "image/jpeg", None, "clear"),
        ("notice.webp", _encoded(image, "WEBP"), "image/webp", None, "clear"),
        (
            "blurred.png",
            _encoded(image.filter(ImageFilter.GaussianBlur(5))),
            "image/png",
            None,
            "blurred",
        ),
        ("low-contrast.png", _encoded(low), "image/png", None, "low_contrast"),
        (
            "rotated.png",
            _encoded(image.transpose(Image.Transpose.ROTATE_90)),
            "image/png",
            None,
            "rotated",
        ),
        ("tiny.png", _encoded(image.resize((16, 6))), "image/png", None, "tiny"),
        ("truncated.png", plain[:40], "image/png", "MALFORMED_INPUT", "truncated"),
        ("wrong-mime.png", plain, "image/jpeg", "MALFORMED_INPUT", "mime_mismatch"),
        ("animated.png", animated, "image/png", "MALFORMED_INPUT", "multiple_frames"),
        (
            "spoofed.png",
            b"\x89PNG\r\n\x1a\nSYNTHETIC_INVALID",
            "image/png",
            "MALFORMED_INPUT",
            "spoofed",
        ),
        (
            "orientation.jpg",
            _encoded(image, "JPEG", exif=orientation),
            "image/jpeg",
            None,
            "exif_orientation",
        ),
    ]
    pcm = _pcm()
    wrong_size = bytearray(pcm)
    struct.pack_into("<I", wrong_size, 4, 0xFFFFFFFF)
    partial = bytearray(pcm[:-1])
    struct.pack_into("<I", partial, 40, len(partial) - 44)
    floating = bytearray(pcm)
    struct.pack_into("<H", floating, 20, 3)
    extended = bytearray(pcm[20:36])
    struct.pack_into("<H", extended, 0, 0xFFFE)
    subtype = struct.pack("<IHH", 1, 0, 0x10) + b"\x80\x00\x00\xaa\x00\x38\x9b\x71"

    def extensible(mask):
        fmt = extended + struct.pack("<HHI", 22, 16, mask) + subtype
        return _riff_size(pcm[:12] + b"fmt " + struct.pack("<I", 40) + fmt + pcm[36:])

    sounds = [
        ("tone.wav", pcm, "audio/wav", None, "non_speech_tone"),
        ("noise.wav", _pcm("noise"), "audio/wav", None, "non_speech_noise"),
        ("silence.wav", _pcm("silence"), "audio/wav", None, "silence"),
        ("clipped.wav", _pcm("clipped"), "audio/wav", None, "clipped_signal"),
        ("stereo.wav", _pcm(channels=2), "audio/wav", None, "stereo_tone"),
        ("truncated.wav", pcm[:-1], "audio/wav", "MALFORMED_INPUT", "truncated"),
        ("wrong-size.wav", bytes(wrong_size), "audio/wav", "MALFORMED_INPUT", "declared_size"),
        ("partial-frame.wav", _riff_size(partial), "audio/wav", "MALFORMED_INPUT", "partial_frame"),
        ("float.wav", bytes(floating), "audio/wav", "UNSUPPORTED_INPUT", "unsupported_codec"),
        ("empty.wav", b"", "audio/wav", "MALFORMED_INPUT", "empty"),
        ("bad-mask.wav", extensible(3), "audio/wav", "MALFORMED_INPUT", "channel_mask"),
        ("extensible.wav", extensible(4), "audio/wav", None, "extensible_tone"),
    ]
    cases = []
    root.mkdir(parents=True)
    for kind, values in (("IMAGE", images), ("AUDIO", sounds)):
        for number, (name, data, mime, error, condition) in enumerate(values, 1):
            (root / name).write_bytes(data)
            cases.append(
                {
                    "id": f"DM{kind[0]}-{number:02}",
                    "kind": kind,
                    "file": name,
                    "source_group": "D-MEDIA-DOCUMENT-01"
                    if kind == "IMAGE"
                    else "D-MEDIA-SIGNAL-01",
                    "split": "development",
                    "source": "synthetic",
                    "media_type": mime,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                    "condition": condition,
                    "expected_error": error,
                    "conversion_evaluated": False,
                    "model_evaluated": False,
                }
            )
    image_value = {
        "kind": "DOCUMENT_IMAGE",
        "complete": True,
        "segments": [{"text": "SYNTHETIC NOTICE", "page": 1}],
    }
    audio_value = {
        "kind": "AUDIO",
        "complete": True,
        "duration_ms": 100,
        "segments": [{"text": "CONTROLLED REPLAY NOT TRANSCRIPTION", "start_ms": 0, "end_ms": 100}],
    }
    from copy import deepcopy

    failures = []
    for kind, reason, error in [
        ("TEXT", "blank", "MALFORMED_INPUT"),
        ("TEXT", "too_long", "MALFORMED_INPUT"),
        ("TEXT", "surrogate", "MALFORMED_INPUT"),
        ("TEXT", "wrong_type", "MALFORMED_INPUT"),
        ("IMAGE", "partial", "INCOMPLETE_OUTPUT"),
        ("IMAGE", "empty", "INCOMPLETE_OUTPUT"),
        ("IMAGE", "wrong_page", "SCHEMA_MISMATCH"),
        ("IMAGE", "unknown_field", "SCHEMA_MISMATCH"),
        ("AUDIO", "partial", "INCOMPLETE_OUTPUT"),
        ("AUDIO", "empty", "INCOMPLETE_OUTPUT"),
        ("AUDIO", "missing_time", "SCHEMA_MISMATCH"),
        ("AUDIO", "outside_duration", "SCHEMA_MISMATCH"),
    ]:
        value = deepcopy(image_value if kind == "IMAGE" else audio_value)
        if kind == "TEXT":
            value = reason  # Recipes avoid storing 10k repeated characters/surrogates.
        elif reason == "partial":
            value["complete"] = False
        elif reason == "empty":
            value["segments"] = []
        elif reason == "wrong_page":
            value["segments"][0]["page"] = 2
        elif reason == "unknown_field":
            value["raw_payload"] = "REJECT_ME"
        elif reason == "missing_time":
            value["segments"][0].pop("end_ms")
        else:
            value["segments"][0]["end_ms"] = 101
        failures.append(
            {
                "id": f"DF-{len(failures) + 1:02}",
                "kind": kind,
                "value": value,
                "expected_error": error,
                "scope": "CONTROLLED_FAILURE_REPLAY",
            }
        )
    manifest = {
        "schema_version": "d-media-safety-0.1",
        "source": "synthetic",
        "purpose": (
            "Byte validation/failure replay; not OCR/STT/model performance or labelled60 corpus"
        ),
        "generator": {"python": sys.version.split()[0], "pillow": pillow_version},
        "audio_has_speech": False,
        "conversion_evaluation": "NOT_RUN",
        "cases": cases,
        "failure_replays": failures,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


async def check(root: Path) -> dict:
    if root.is_symlink() or (root / "manifest.json").is_symlink():
        raise ValueError("fixture symlink")
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["schema_version"] != "d-media-safety-0.1" or manifest["source"] != "synthetic":
        raise ValueError("fixture version/source")
    cases = manifest["cases"]
    if len(cases) != 24 or len({c["id"] for c in cases}) != 24:
        raise ValueError("expected 24 distinct media byte cases")
    rows, names = [], set()
    for case in cases:
        if (
            case.get("source") != "synthetic"
            or case.get("split") != "development"
            or case.get("conversion_evaluated") is not False
            or case.get("model_evaluated") is not False
        ):
            raise ValueError("fixture provenance/evaluation scope")
        name = case["file"]
        if (
            not isinstance(name, str)
            or name in {".", ".."}
            or Path(name).name != name
            or name in names
        ):
            raise ValueError("unsafe or duplicate fixture filename")
        names.add(name)
        path = root / name
        if path.is_symlink() or path.stat().st_size > MAX_AUDIO_BYTES:
            raise ValueError("fixture symlink or size")
        data = path.read_bytes()
        if len(data) != case["bytes"] or hashlib.sha256(data).hexdigest() != case["sha256"]:
            raise ValueError("fixture digest/size mismatch")
        error = None
        try:
            if case["kind"] == "IMAGE":
                SemanticInput(
                    image_base64=base64.b64encode(data).decode(),
                    image_media_type=case["media_type"],
                )
            elif case["kind"] == "AUDIO":
                inspect_pcm_wav(data, case["media_type"])
            else:
                raise ValueError("fixture kind")
        except ValidationError:
            error = "MALFORMED_INPUT"
        except AnalyzerError as problem:
            error = problem.code.value
        rows.append(
            {"id": case["id"], "passed": error == case["expected_error"], "error_code": error}
        )
    if {p.name for p in root.iterdir()} != names | {"manifest.json"}:
        raise ValueError("unlisted fixture files")
    replays = manifest["failure_replays"]
    if len(replays) != 12 or len({c["id"] for c in replays}) != 12:
        raise ValueError("expected twelve distinct failure replays")
    calls, replay_rows = 0, []

    async def forbidden(text):
        nonlocal calls
        calls += 1
        raise AssertionError("invalid conversion reached processor")

    for case in replays:
        error = None
        try:
            if case["kind"] == "TEXT":
                recipes = {
                    "blank": " ",
                    "too_long": "x" * 10001,
                    "surrogate": "\ud800",
                    "wrong_type": {},
                }
                await PhishingAnalyzer(MockLLMProvider())(recipes[case["value"]])
            else:
                await analyze_conversion(case["value"], forbidden)
        except AnalyzerError as problem:
            error = problem.code.value
        replay_rows.append(
            {"id": case["id"], "passed": error == case["expected_error"], "error_code": error}
        )
    passed = all(row["passed"] for row in rows + replay_rows) and calls == 0
    return {
        "status": "OFFLINE_MEDIA_CONTRACT_PASS" if passed else "FAIL",
        "media_cases": rows,
        "failure_replays": replay_rows,
        "processor_calls": calls,
        "paid_calls": 0,
        "semantic_evaluation": "NOT_RUN",
        "holdout_predictions": 0,
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.generate:
        generate(args.root)
    report = asyncio.run(check(args.root))
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(text)
    print(text, end="")
    return 0 if report["status"] == "OFFLINE_MEDIA_CONTRACT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
