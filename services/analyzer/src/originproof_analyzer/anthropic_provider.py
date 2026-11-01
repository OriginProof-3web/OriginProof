"""Claude analysis for members who saved an Anthropic key. Same report contract as GPT."""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from importlib.resources import files
from typing import Literal

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    DefaultAsyncHttpxClient,
    RateLimitError,
    transform_schema,
)
from originproof_core import CardPaymentNoticeCandidate
from originproof_core.wallet_contract import AnalysisReport
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .converted_inputs import ConvertedText, prepare_conversion
from .errors import AnalyzerError, AnalyzerErrorCode
from .inputs import SemanticInput
from .media_converters import IMAGE_INSTRUCTIONS
from .providers import ANALYSIS_PROMPT_VERSION, _AnalysisOutput

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicSettings(BaseSettings):
    # Separate from AnalyzerSettings: that file is pinned by the frozen evaluation candidate.
    model_config = SettingsConfigDict(extra="ignore", env_file=None, hide_input_in_errors=True)

    anthropic_model: str = Field(default="claude-opus-5-5", min_length=1, pattern=r"^\S+$")
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"
    anthropic_timeout_seconds: float = Field(default=90, gt=0, allow_inf_nan=False)
    llm_max_retries: int = Field(default=2, ge=0, le=2)


def member_client(key: str, on_response=None) -> AsyncAnthropic:
    """Pinned endpoint and no ambient proxy, so a member key only ever goes to Anthropic."""
    return AsyncAnthropic(
        api_key=key,
        base_url="https://api.anthropic.com",
        http_client=DefaultAsyncHttpxClient(
            trust_env=False,
            follow_redirects=False,
            event_hooks={"response": [on_response] if on_response else []},
        ),
    )


@contextmanager
def _provider_errors():
    try:
        yield
    except APITimeoutError:
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT) from None
    except RateLimitError:
        raise AnalyzerError(AnalyzerErrorCode.RATE_LIMIT) from None
    except (ValueError, TypeError, ValidationError):
        raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH) from None
    except (APIConnectionError, APIStatusError):
        raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE) from None


def _output_text(message) -> str:
    if message.stop_reason == "refusal":
        raise AnalyzerError(AnalyzerErrorCode.REFUSAL)
    if message.stop_reason == "max_tokens":
        raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT)
    parts = [block.text for block in message.content if block.type == "text"]
    if len(parts) != 1:
        raise AnalyzerError(AnalyzerErrorCode.INCOMPLETE_OUTPUT)
    return parts[0]


async def _structured(client, settings, system, content, schema, timeout) -> str:
    message = await client.with_options(
        timeout=timeout, max_retries=settings.llm_max_retries
    ).beta.messages.create(
        model=settings.anthropic_model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_config={
            "effort": settings.anthropic_effort,
            "format": {"type": "json_schema", "schema": transform_schema(schema)},
        },
        betas=[FALLBACK_BETA],
        fallbacks="default",
    )
    return _output_text(message)


class AnthropicLLMProvider:
    provider_name = "anthropic"
    image_mode = "vision"
    evidence_offset_mode = "QUOTE_ONLY_DETERMINISTIC_UNIQUE_MATCH"

    def __init__(self, settings: AnthropicSettings, client: AsyncAnthropic) -> None:
        self.model = settings.anthropic_model
        self._settings = settings
        self._client = client

    def extract_card_payment_notice(self, artifact: SemanticInput) -> CardPaymentNoticeCandidate:
        # Only the analysis job uses member keys; the legacy extractor stays on the server path.
        raise AnalyzerError(AnalyzerErrorCode.UNSUPPORTED_INPUT)

    async def analyze_phishing(self, text: str) -> AnalysisReport:
        prompt = (
            files("originproof_analyzer")
            .joinpath("prompts", f"{ANALYSIS_PROMPT_VERSION}.md")
            .read_text(encoding="utf-8")
        )
        with _provider_errors():
            body = await _structured(
                self._client,
                self._settings,
                prompt,
                [{"type": "text", "text": text}],
                _AnalysisOutput,
                self._settings.anthropic_timeout_seconds,
            )
            data = json.loads(body)
            if not isinstance(data, dict) or set(data) != set(_AnalysisOutput.model_fields):
                raise ValueError("expected all shared analysis fields")
            value = _AnalysisOutput.model_validate_json(body, strict=True)
            return AnalysisReport.model_validate(value.model_dump())


async def document_image_to_text(
    artifact: SemanticInput, *, settings: AnthropicSettings, client, remaining_seconds: float
) -> ConvertedText:
    deadline = asyncio.get_running_loop().time() + remaining_seconds
    try:
        async with asyncio.timeout_at(deadline):
            with _provider_errors():
                body = await _structured(
                    client,
                    settings,
                    IMAGE_INSTRUCTIONS,
                    [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": artifact.image_media_type,
                                "data": artifact.image_base64,
                            },
                        },
                        {"type": "text", "text": "Transcribe this document image."},
                    ],
                    ConvertedText,
                    min(
                        settings.anthropic_timeout_seconds,
                        deadline - asyncio.get_running_loop().time(),
                    ),
                )
                value = json.loads(body)
                if not isinstance(value, dict) or set(value) != set(ConvertedText.model_fields):
                    raise ValueError("incomplete converter fields")
                result = ConvertedText.model_validate_json(body, strict=True)
                if result.kind != "DOCUMENT_IMAGE":
                    raise ValueError("image conversion kind")
                prepare_conversion(result)
    except TimeoutError:
        raise AnalyzerError(AnalyzerErrorCode.TIMEOUT) from None
    return result
