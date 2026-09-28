from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from importlib.resources import files
from typing import Protocol

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    OpenAI,
    RateLimitError,
)
from originproof_core import CardPaymentNoticeCandidate
from pydantic import ValidationError

from .errors import AnalyzerError, AnalyzerErrorCode
from .inputs import SemanticInput
from .settings import AnalyzerSettings
from .validation import EXTRACTED_FIELDS, validate_candidate

PROMPT_VERSION = "card_payment_notice_v3"


class LLMProvider(Protocol):
    provider_name: str
    model: str

    def extract_card_payment_notice(
        self, artifact: SemanticInput
    ) -> CardPaymentNoticeCandidate: ...


LABELS = {
    "issuer_name": r"(?:발행자|issuer)",
    "masked_card": r"(?:카드|card)",
    "amount_minor": r"(?:금액|amount)",
    "merchant": r"(?:가맹점|merchant)",
    "approved_at": r"(?:승인시각|approved[_ ]?at)",
    "transaction_id": r"(?:거래[ _]?id|transaction[ _]?id)",
    "proof_id": r"(?:proof[ _]?id)",
}


def _parse_mock_text(text: str) -> CardPaymentNoticeCandidate:
    raw: dict[str, str] = {}

    def record(name: str, value: str) -> None:
        if name in raw and raw[name] != value:
            raise ValueError("conflicting extracted values")
        raw[name] = value

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line in {"카드 승인", "Card approved", "SYNTHETIC FIXTURE"}:
            continue
        for name, label in LABELS.items():
            match = re.fullmatch(rf"{label}\s*:\s*(.*)", line, re.IGNORECASE)
            if match:
                record(name, match[1])
                break
        else:
            if match := re.fullmatch(r"\[([^\[\]]+)\]", line):
                record("issuer_name", match[1])
            elif match := re.fullmatch(r"(?:카드|card)\s+([*xX-]+[0-9]+)", line):
                record("masked_card", match[1])
            elif re.fullmatch(r"[-+0-9,.]+\s*(?:원|KRW)", line, re.IGNORECASE):
                record("amount_minor", line)
                # In the README template the merchant sits between amount and timestamp.
                if index + 2 < len(lines) and re.match(r"^[0-9]{4}-", lines[index + 2]):
                    record("merchant", lines[index + 1])
            elif re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T]", line):
                record("approved_at", line)

    values: dict[str, object] = dict.fromkeys(EXTRACTED_FIELDS)
    for name in ("issuer_name", "merchant", "transaction_id", "proof_id"):
        if name in raw:
            values[name] = raw[name]
    if "masked_card" in raw:
        match = re.fullmatch(r"[*xX-]+([0-9]{4})", raw["masked_card"])
        if not match:
            raise ValueError("invalid masked card")
        values["masked_card"] = match[1]
    if "amount_minor" in raw:
        match = re.fullmatch(
            r"([1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)\s*(원|KRW)",
            raw["amount_minor"],
            re.IGNORECASE,
        )
        if not match:
            raise ValueError("invalid KRW amount")
        values["amount_minor"] = int(match[1].replace(",", ""))
        values["currency"] = "KRW"
    if "approved_at" in raw:
        stamp = raw["approved_at"]
        if stamp.endswith(" KST"):
            stamp = stamp[:-4]
        if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}", stamp):
            raise ValueError("invalid approval time")
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=9)))
        values["approved_at"] = parsed.astimezone(UTC)
    missing = [name for name in EXTRACTED_FIELDS if values[name] is None]
    return validate_candidate(
        CardPaymentNoticeCandidate.model_validate(
            {
                **values,
                "confidence": round(
                    0.98 * (len(EXTRACTED_FIELDS) - len(missing)) / len(EXTRACTED_FIELDS), 4
                ),
                "missing_fields": missing,
            },
            strict=True,
        )
    )


class MockLLMProvider:
    """Template parser and opt-in hash-based image replay; NOT OCR or model evaluation.

    Image replay and fault injection are constructor-only test dependencies. HTTP callers
    cannot supply expected fields, a transcript override, or a simulated error code.
    """

    provider_name = "mock"
    model = "deterministic-template-v3"

    def __init__(
        self,
        *,
        image_replays: Mapping[str, str] | None = None,
        error: AnalyzerErrorCode | None = None,
    ) -> None:
        self._image_replays = dict(image_replays or {})
        self._error = error

    @property
    def image_mode(self) -> str:
        return "fixture_replay_only" if self._image_replays else "unsupported"

    def extract_card_payment_notice(self, artifact: SemanticInput) -> CardPaymentNoticeCandidate:
        if self._error is not None:
            raise AnalyzerError(self._error)
        text = artifact.text
        if text is None:
            digest = hashlib.sha256(base64.b64decode(artifact.image_base64)).hexdigest()
            text = self._image_replays.get(digest)
            if text is None:
                raise AnalyzerError(AnalyzerErrorCode.UNSUPPORTED_INPUT)
        try:
            return _parse_mock_text(text)
        except (ValueError, ValidationError):
            raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH) from None


def _structured_text(envelope: object) -> str:
    if not isinstance(envelope, dict):
        raise ValueError("invalid response envelope")
    if envelope.get("status") == "incomplete":
        raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT)
    parts = []
    for item in envelope.get("output") or []:
        if not isinstance(item, dict):
            raise ValueError("invalid output item")
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                raise ValueError("invalid output part")
            if part.get("type") == "refusal":
                raise AnalyzerError(AnalyzerErrorCode.REFUSAL)
            if part.get("type") == "output_text":
                parts.append(part.get("text"))
    if envelope.get("status") != "completed":
        raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE)
    if not parts:
        raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT)
    if len(parts) != 1 or not isinstance(parts[0], str):
        raise ValueError("expected one structured output")
    return parts[0]


class OpenAILLMProvider:
    provider_name = "openai"
    image_mode = "vision"

    def __init__(self, settings: AnalyzerSettings, *, client: OpenAI | None = None) -> None:
        self.model = settings.openai_model
        self._settings = settings
        self._client = client
        self._prompt = (
            files("originproof_analyzer")
            .joinpath(
                "prompts",
                f"{PROMPT_VERSION}.md",
            )
            .read_text(encoding="utf-8")
        )

    def _get_client(self) -> OpenAI:
        # Lazy construction keeps import/health checks independent of a paid key.
        if self._client is None:
            key = self._settings.openai_api_key
            if key is None or not key.get_secret_value().strip():
                raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE)
            self._client = OpenAI(api_key=key.get_secret_value())
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def extract_card_payment_notice(self, artifact: SemanticInput) -> CardPaymentNoticeCandidate:
        if artifact.text is not None:
            content = [{"type": "input_text", "text": artifact.text}]
        else:
            content = [
                {
                    "type": "input_image",
                    "detail": "high",
                    "image_url": f"data:{artifact.image_media_type};base64,{artifact.image_base64}",
                }
            ]
        try:
            # SDK is the only retry owner; at most 2 retries (3 attempts), each with a timeout.
            client = self._get_client().with_options(
                timeout=self._settings.llm_timeout_seconds,
                max_retries=self._settings.llm_max_retries,
            )
            raw = client.responses.with_raw_response.parse(
                model=self.model,
                instructions=self._prompt,
                input=[{"role": "user", "content": content}],
                text_format=CardPaymentNoticeCandidate,
                reasoning={"effort": self._settings.openai_reasoning_effort},
                max_output_tokens=4096,
                store=False,
            )
            # Check refusal/incomplete BEFORE the SDK tries to parse possibly truncated JSON.
            text = _structured_text(raw.http_response.json())
            # Strict JSON validation prevents SDK/Pydantic coercion of booleans or strings to ints.
            data = json.loads(text)
            if not isinstance(data, dict) or set(data) != set(
                CardPaymentNoticeCandidate.model_fields
            ):
                raise ValueError("structured output must contain all contract fields")
            candidate = CardPaymentNoticeCandidate.model_validate_json(text, strict=True)
            response = raw.parse()
            if response.output_parsed is None:
                raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT)
            return validate_candidate(candidate)
        except APITimeoutError:
            raise AnalyzerError(AnalyzerErrorCode.TIMEOUT) from None
        except RateLimitError:
            raise AnalyzerError(AnalyzerErrorCode.RATE_LIMIT) from None
        except LengthFinishReasonError:
            raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT) from None
        except ContentFilterFinishReasonError:
            raise AnalyzerError(AnalyzerErrorCode.REFUSAL) from None
        except (APIResponseValidationError, ValueError, TypeError, ValidationError):
            raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH) from None
        except (APIConnectionError, APIStatusError):
            raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE) from None
