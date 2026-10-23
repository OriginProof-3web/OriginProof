"""Offline PCM WAV inspection only; no upload route, transcription or provider call."""

from __future__ import annotations

import struct
import wave
from dataclasses import dataclass
from io import BytesIO

from .errors import AnalyzerError, AnalyzerErrorCode

MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_AUDIO_SECONDS = 300


@dataclass(frozen=True)
class PCMInfo:
    """Decoder metadata only; never retain audio bytes in a result or its repr."""

    channels: int
    sample_rate: int
    sample_width: int
    frames: int
    duration_ms: int


def inspect_pcm_wav(data: bytes, media_type: str) -> PCMInfo:
    """Validate a bounded complete RIFF/PCM stream; unsupported codecs stay explicit."""
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_AUDIO_BYTES:
        raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT)
    if not isinstance(media_type, str) or media_type not in {"audio/wav", "audio/x-wav"}:
        raise AnalyzerError(AnalyzerErrorCode.UNSUPPORTED_INPUT)
    try:
        if (
            len(data) < 12
            or data[:4] != b"RIFF"
            or data[8:12] != b"WAVE"
            or struct.unpack_from("<I", data, 4)[0] != len(data) - 8
        ):
            raise ValueError
        position, fmt, pcm_size = 12, None, None
        while position < len(data):
            if position + 8 > len(data):
                raise ValueError
            kind, size = struct.unpack_from("<4sI", data, position)
            start, end = position + 8, position + 8 + size
            if end > len(data):
                raise ValueError
            if kind == b"fmt ":
                if fmt is not None or pcm_size is not None or size < 16:
                    raise ValueError
                fmt = struct.unpack_from("<HHIIHH", data, start)
                if fmt[0] == 0xFFFE:
                    if size < 40:
                        raise ValueError
                    extension, precision, mask = struct.unpack_from("<HHI", data, start + 16)
                    if (
                        extension < 22
                        or 18 + extension > size
                        or precision > fmt[5]
                        or (mask and mask.bit_count() != fmt[1])
                    ):
                        raise ValueError
            elif kind == b"data":
                if fmt is None or pcm_size is not None:
                    raise ValueError
                pcm_size = size
            # Python's WAV writer omits final odd data padding; permit EOF at payload end.
            position = end if end == len(data) else end + (size % 2)
        if position != len(data) or fmt is None or pcm_size is None:
            raise ValueError
        encoding, channels, rate, byte_rate, alignment, bits = fmt
        if encoding not in {1, 0xFFFE}:  # Python wave also validates extensible PCM subtype.
            raise AnalyzerError(AnalyzerErrorCode.UNSUPPORTED_INPUT)
        if (
            channels not in {1, 2}
            or rate <= 0
            or bits not in {8, 16, 24, 32}
            or alignment != channels * (bits // 8)
            or byte_rate != rate * alignment
            or pcm_size == 0
            or pcm_size % alignment
            or pcm_size // alignment > rate * MAX_AUDIO_SECONDS
        ):
            raise ValueError
        with wave.open(BytesIO(data), "rb") as decoded:
            frames = decoded.getnframes()
            if (
                decoded.getcomptype() != "NONE"
                or decoded.getnchannels() != channels
                or decoded.getsampwidth() != bits // 8
                or decoded.getframerate() != rate
                or frames != pcm_size // alignment
                or len(decoded.readframes(frames + 1)) != pcm_size
            ):
                raise ValueError
        return PCMInfo(channels, rate, bits // 8, frames, (frames * 1000 + rate - 1) // rate)
    except (ValueError, EOFError, struct.error, wave.Error, OSError):
        # Discard parser details: they may include untrusted media or metadata.
        raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT) from None
