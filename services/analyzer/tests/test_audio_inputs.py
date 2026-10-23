"""Actual in-memory PCM decoding and hostile headers; no speech recognition or network."""

import socket
import struct
import wave
from dataclasses import asdict
from io import BytesIO

import pytest
from originproof_analyzer.audio_inputs import MAX_AUDIO_BYTES, inspect_pcm_wav
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode


def pcm(*, channels=1, width=2, rate=8000, frames=80):
    output = BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setparams((channels, width, rate, frames, "NONE", "not compressed"))
        # Synthetic sample bytes, not a recording or a claim of intelligible speech.
        writer.writeframes(b"\x00" * (frames * channels * width))
    return output.getvalue()


def size_header(data):
    value = bytearray(data)
    struct.pack_into("<I", value, 4, len(value) - 8)
    return bytes(value)


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("audio inspection must be offline")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.mark.parametrize("channels,width", [(1, 1), (1, 2), (2, 3), (2, 4)])
def test_actual_pcm_decode_returns_metadata_and_never_payload(channels, width):
    data = pcm(channels=channels, width=width, frames=81)
    info = inspect_pcm_wav(data, "audio/wav")
    assert asdict(info) == {
        "channels": channels,
        "sample_rate": 8000,
        "sample_width": width,
        "frames": 81,
        "duration_ms": 11,
    }
    assert data.hex() not in repr(info)
    assert len(data) < MAX_AUDIO_BYTES


@pytest.mark.parametrize("frames,accepted", [(8000 * 300, True), (8000 * 300 + 1, False)])
def test_duration_boundary_is_exact_not_rounded_down(frames, accepted):
    data = pcm(frames=frames)
    if accepted:
        assert inspect_pcm_wav(data, "audio/x-wav").duration_ms == 300_000
    else:
        with pytest.raises(AnalyzerError) as exc:
            inspect_pcm_wav(data, "audio/wav")
        assert exc.value.code == AnalyzerErrorCode.MALFORMED_INPUT


@pytest.mark.parametrize(
    "kind",
    [
        "empty",
        "not_bytes",
        "over_size",
        "signature",
        "truncated",
        "riff_size",
        "partial_frame",
        "declared_long",
        "trailing_junk",
        "zero_frames",
        "channels",
        "alignment",
        "byte_rate",
        "zero_rate",
        "missing_data",
        "duplicate_data",
        "duplicate_fmt",
    ],
)
def test_malformed_or_resource_exceeding_audio_fails_without_partial_success(kind, caplog):
    data = bytearray(pcm())
    if kind == "empty":
        data = b""
    elif kind == "not_bytes":
        data = "PRIVATE_SYNTHETIC_BYTES"
    elif kind == "over_size":
        data = b"x" * (MAX_AUDIO_BYTES + 1)
    elif kind == "signature":
        data[:4] = b"ID3!"
    elif kind == "truncated":
        data = data[:-1]
    elif kind == "riff_size":
        struct.pack_into("<I", data, 4, 0xFFFFFFFF)
    elif kind == "partial_frame":
        data = data[:-1]
        struct.pack_into("<I", data, 40, len(data) - 44)
        data = size_header(data)
    elif kind == "declared_long":
        struct.pack_into("<I", data, 40, 0xFFFFFFFE)
    elif kind == "trailing_junk":
        data = size_header(data + b"PRIVATE_SYNTHETIC_BYTES")
    elif kind == "zero_frames":
        data = pcm(frames=0)
    elif kind == "channels":
        data = pcm(channels=3)
    elif kind == "alignment":
        struct.pack_into("<H", data, 32, 1)
    elif kind == "byte_rate":
        struct.pack_into("<I", data, 28, 1)
    elif kind == "zero_rate":
        struct.pack_into("<I", data, 24, 0)
    elif kind == "missing_data":
        data = size_header(data[:36])
    elif kind == "duplicate_data":
        data = size_header(data + data[36:])
    else:
        data = size_header(data[:36] + data[12:36] + data[36:])
    if isinstance(data, bytearray):
        data = bytes(data)
    with pytest.raises(AnalyzerError) as exc:
        inspect_pcm_wav(data, "audio/wav")
    assert exc.value.code == AnalyzerErrorCode.MALFORMED_INPUT
    assert exc.value.as_response()["error"]["message"] == "Input failed validation."
    assert "PRIVATE_SYNTHETIC_BYTES" not in str(exc.value) + caplog.text


@pytest.mark.parametrize(
    "media_type", ["audio/mpeg", "audio/mp4", "video/mp4", "image/png", None, []]
)
def test_unimplemented_media_never_pretends_to_be_supported(media_type):
    with pytest.raises(AnalyzerError) as exc:
        inspect_pcm_wav(pcm(), media_type)
    assert exc.value.code == AnalyzerErrorCode.UNSUPPORTED_INPUT


def test_float_wave_is_unsupported_and_not_silently_read_as_integer_pcm():
    data = bytearray(pcm())
    struct.pack_into("<H", data, 20, 3)
    with pytest.raises(AnalyzerError) as exc:
        inspect_pcm_wav(bytes(data), "audio/wav")
    assert exc.value.code == AnalyzerErrorCode.UNSUPPORTED_INPUT


def test_valid_bounded_metadata_chunk_is_not_mistaken_for_audio_or_logged(caplog):
    data = pcm()
    junk = b"JUNK" + struct.pack("<I", 4) + b"NOTE"
    info = inspect_pcm_wav(size_header(data[:12] + junk + data[12:]), "audio/wav")
    assert info.frames == 80 and "NOTE" not in caplog.text


def test_exact_twenty_mib_stream_is_accepted_before_above_limit_is_rejected():
    frames = (MAX_AUDIO_BYTES - 44) // 2
    data = pcm(rate=48000, frames=frames)
    assert len(data) == MAX_AUDIO_BYTES
    assert inspect_pcm_wav(data, "audio/wav").frames == frames


@pytest.mark.parametrize("pcm_subtype", [True, False])
def test_extensible_wav_subtype_is_checked_by_the_actual_decoder(pcm_subtype):
    data = pcm()
    fmt = bytearray(data[20:36])
    struct.pack_into("<H", fmt, 0, 0xFFFE)
    # KSDATAFORMAT_SUBTYPE_PCM; IEEE float changes only the first GUID word.
    subtype = struct.pack("<IHH", 1 if pcm_subtype else 3, 0, 0x10)
    subtype += b"\x80\x00\x00\xaa\x00\x38\x9b\x71"
    extended = fmt + struct.pack("<HHI", 22, 16, 4) + subtype
    output = size_header(data[:12] + b"fmt " + struct.pack("<I", 40) + extended + data[36:])
    if pcm_subtype:
        assert inspect_pcm_wav(output, "audio/wav").frames == 80
    else:
        with pytest.raises(AnalyzerError) as exc:
            inspect_pcm_wav(output, "audio/wav")
        assert exc.value.code == AnalyzerErrorCode.MALFORMED_INPUT
