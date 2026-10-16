import logging
from time import perf_counter

from originproof_core import CardPaymentNoticeCandidate
from pydantic import ValidationError

from .errors import AnalyzerError, AnalyzerErrorCode
from .inputs import SemanticInput
from .providers import PROMPT_VERSION, LLMProvider
from .validation import validate_candidate

logger = logging.getLogger(__name__)


class SemanticInterface:
    def __init__(self, provider: LLMProvider, *, minimum_confidence: float = 0.70) -> None:
        if not 0 <= minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self.provider = provider
        self.minimum_confidence = minimum_confidence

    def analyze_card_payment_notice(self, artifact: SemanticInput) -> CardPaymentNoticeCandidate:
        started = perf_counter()
        error_code = None
        try:
            try:
                # Revalidate even trusted-looking model instances and model_construct test doubles.
                artifact = SemanticInput.model_validate(artifact.model_dump(warnings=False))
            except (ValueError, ValidationError):
                raise AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT) from None
            try:
                candidate = validate_candidate(self.provider.extract_card_payment_notice(artifact))
            except (ValueError, TypeError, AttributeError, ValidationError):
                raise AnalyzerError(AnalyzerErrorCode.SCHEMA_MISMATCH) from None
            if candidate.confidence < self.minimum_confidence:
                raise AnalyzerError(AnalyzerErrorCode.LOW_CONFIDENCE)
            return candidate
        except AnalyzerError as exc:
            error_code = exc.code.value
            raise
        finally:
            # Metadata only: never a candidate, input, image hash, API key, or raw model response.
            logger.info(
                "analyzer.extraction",
                extra={
                    "analyzer": {
                        "provider": self.provider.provider_name,
                        "model": self.provider.model,
                        "prompt_version": PROMPT_VERSION,
                        "input_kind": artifact.kind,
                        "duration_ms": round((perf_counter() - started) * 1000),
                        "error_code": error_code,
                    }
                },
            )
