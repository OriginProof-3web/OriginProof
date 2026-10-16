from enum import StrEnum


class AnalyzerErrorCode(StrEnum):
    MALFORMED_INPUT = "MALFORMED_INPUT"
    UNSUPPORTED_INPUT = "UNSUPPORTED_INPUT"
    REFUSAL = "REFUSAL"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    INCOMPLETE_OUTPUT = "INCOMPLETE_OUTPUT"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


MESSAGES = {
    AnalyzerErrorCode.MALFORMED_INPUT: "Input failed validation.",
    AnalyzerErrorCode.UNSUPPORTED_INPUT: "Input is not supported by this provider.",
    AnalyzerErrorCode.REFUSAL: "Provider declined extraction.",
    AnalyzerErrorCode.TIMEOUT: "Extraction request timed out.",
    AnalyzerErrorCode.RATE_LIMIT: "Extraction provider is rate limited.",
    AnalyzerErrorCode.INCOMPLETE_OUTPUT: "Provider returned incomplete output.",
    AnalyzerErrorCode.SCHEMA_MISMATCH: "Extraction failed candidate validation.",
    AnalyzerErrorCode.LOW_CONFIDENCE: "Extraction confidence is below the configured threshold.",
    AnalyzerErrorCode.PROVIDER_UNAVAILABLE: "Extraction provider is unavailable.",
}

HTTP_STATUS = {
    AnalyzerErrorCode.MALFORMED_INPUT: 422,
    AnalyzerErrorCode.UNSUPPORTED_INPUT: 422,
    AnalyzerErrorCode.REFUSAL: 422,
    AnalyzerErrorCode.TIMEOUT: 504,
    AnalyzerErrorCode.RATE_LIMIT: 503,
    AnalyzerErrorCode.INCOMPLETE_OUTPUT: 502,
    AnalyzerErrorCode.SCHEMA_MISMATCH: 502,
    AnalyzerErrorCode.LOW_CONFIDENCE: 422,
    AnalyzerErrorCode.PROVIDER_UNAVAILABLE: 503,
}


class AnalyzerError(Exception):
    """Only fixed, safe messages cross the provider boundary."""

    def __init__(self, code: AnalyzerErrorCode) -> None:
        self.code = AnalyzerErrorCode(code)
        super().__init__(MESSAGES[self.code])

    def as_response(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code.value, "message": MESSAGES[self.code]}}
