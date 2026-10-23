"""D-internal post-conversion analysis, not an OCR/STT provider or an HTTP contract."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

from originproof_core.wallet_contract import AnalysisReport
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import AnalyzerError, AnalyzerErrorCode
from .inputs import SemanticInput
from .phishing import validate_analysis_report


class ConversionSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    text: str = Field(min_length=1, max_length=10_000, repr=False)
    page: int | None = Field(default=None, ge=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=1)


class ConvertedText(BaseModel):
    """Untrusted converter output; locations/accuracy are declared, not independently verified."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)

    kind: Literal["DOCUMENT_IMAGE", "AUDIO"]
    complete: bool
    duration_ms: int | None = Field(default=None, ge=1, le=300_000)
    segments: list[ConversionSegment] = Field(max_length=10_000, repr=False)


@dataclass(frozen=True)
class SegmentRange:
    start: int
    end: int
    page: int | None
    start_ms: int | None
    end_ms: int | None


@dataclass(frozen=True)
class PreparedText:
    text: str = field(repr=False)
    ranges: tuple[SegmentRange, ...]


def prepare_conversion(value: ConvertedText | dict) -> PreparedText:
    """Reject incomplete output and invalid source spans before any analysis is invoked."""
    try:
        value = ConvertedText.model_validate(
            value.model_dump(warnings=False) if isinstance(value, ConvertedText) else value
        )
    except (ValueError, TypeError, ValidationError):
        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH) from None
    if not value.complete or not value.segments:
        raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT)
    if (value.kind == "AUDIO") != (value.duration_ms is not None):
        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
    pieces, ranges, offset, last_time = [], [], 0, 0
    for segment in value.segments:
        if value.kind == "DOCUMENT_IMAGE":
            valid = segment.page == 1 and segment.start_ms is None and segment.end_ms is None
        else:
            valid = (
                segment.page is None
                and segment.start_ms is not None
                and segment.end_ms is not None
                and last_time <= segment.start_ms < segment.end_ms <= value.duration_ms
            )
            if valid:
                last_time = segment.end_ms
        if not valid or not segment.text.strip():
            raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH)
        if pieces:
            offset += 1  # One declared separator; never trim or normalize converter text.
        end = offset + len(segment.text)
        if end > 10_000:
            raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT)
        try:
            segment.text.encode("utf-8")
        except UnicodeError:
            raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT) from None
        pieces.append(segment.text)
        ranges.append(SegmentRange(offset, end, segment.page, segment.start_ms, segment.end_ms))
        offset = end
    text = SemanticInput(text="\n".join(pieces)).text
    return PreparedText(text, tuple(ranges))


@dataclass(frozen=True)
class EvidenceLocation:
    evidence_index: int
    segment_index: int
    start_offset: int  # Code points within converter segment, not source file bytes.
    end_offset: int
    page: int | None
    start_ms: int | None  # Whole converter segment interval, not word-level timing.
    end_ms: int | None


@dataclass(frozen=True)
class ConvertedAnalysis:
    report: AnalysisReport = field(repr=False)
    locations: tuple[EvidenceLocation, ...]


async def analyze_conversion(
    value: ConvertedText | dict,
    processor: Callable[[str], Awaitable[AnalysisReport]],
    *,
    remaining_seconds: float = 180,
) -> ConvertedAnalysis:
    """Explicit processor injection only; no default provider, retry, key lookup or network."""
    if (
        isinstance(remaining_seconds, bool)
        or not isinstance(remaining_seconds, int | float)
        or not 0 < remaining_seconds <= 180
    ):
        raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + remaining_seconds
    prepared = prepare_conversion(value)
    if loop.time() >= deadline:
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT)
    try:
        async with asyncio.timeout_at(deadline):
            try:
                raw = await processor(prepared.text)
            except (AnalyzerError, TimeoutError, asyncio.CancelledError):
                raise
            except Exception:
                raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE) from None
    except TimeoutError:
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT) from None
    if loop.time() >= deadline:
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT)
    report = validate_analysis_report(raw, prepared.text)
    locations = []
    for index, evidence in enumerate(report.evidence):
        mapped = False
        for segment_index, segment in enumerate(prepared.ranges):
            start = max(evidence.start_offset, segment.start)
            end = min(evidence.end_offset, segment.end)
            if start < end:
                locations.append(
                    EvidenceLocation(
                        index,
                        segment_index,
                        start - segment.start,
                        end - segment.start,
                        segment.page,
                        segment.start_ms,
                        segment.end_ms,
                    )
                )
                mapped = True
        if not mapped:  # An inserted join separator alone is not a media-source quote.
            raise ValueError("GROUNDING_MISMATCH")
    # Reserve trusted scope notices before optional model limitations; keep shared max20.
    notices = ["CONVERSION_ACCURACY_NOT_VERIFIED", "LOCATIONS_ARE_CONVERTER_SEGMENT_SPANS"]
    if len(report.limitations) + len(notices) > 20:
        notices.append("LIMITATIONS_LIMIT_TRUNCATED")
    report = report.model_copy(
        update={
            "limitations": notices + report.limitations[: 20 - len(notices)],
        }
    )
    if loop.time() >= deadline:
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT)
    return ConvertedAnalysis(report, tuple(locations))
