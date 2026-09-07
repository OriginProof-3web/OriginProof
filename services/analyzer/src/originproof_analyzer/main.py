from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from originproof_core import CardPaymentNoticeCandidate

from .errors import HTTP_STATUS, AnalyzerError, AnalyzerErrorCode
from .inputs import SemanticInput
from .providers import MockLLMProvider, OpenAILLMProvider
from .service import SemanticInterface
from .settings import AnalyzerSettings


def create_app(
    service: SemanticInterface | None = None,
    *,
    settings: AnalyzerSettings | None = None,
) -> FastAPI:
    configured = settings or AnalyzerSettings()
    owned_provider = None
    if service is None:
        owned_provider = (
            OpenAILLMProvider(configured)
            if configured.llm_provider == "openai"
            else MockLLMProvider()
        )
        service = SemanticInterface(
            owned_provider,
            minimum_confidence=configured.analyzer_min_confidence,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if isinstance(owned_provider, OpenAILLMProvider):
            owned_provider.close()

    application = FastAPI(title="OriginProof Analyzer", version="0.1.0", lifespan=lifespan)

    @application.exception_handler(RequestValidationError)
    async def invalid_input(_: Request, _exc: RequestValidationError) -> JSONResponse:
        # The default handler echoes input values, including submitted text/base64.
        error = AnalyzerError(AnalyzerErrorCode.MALFORMED_INPUT)
        return JSONResponse(status_code=422, content=error.as_response())

    @application.exception_handler(AnalyzerError)
    async def analyzer_error(_: Request, exc: AnalyzerError) -> JSONResponse:
        return JSONResponse(status_code=HTTP_STATUS[exc.code], content=exc.as_response())

    @application.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @application.get("/v1/capabilities", tags=["analyzer"])
    def capabilities() -> dict[str, str]:
        return {
            "provider": service.provider.provider_name,
            "image_mode": getattr(service.provider, "image_mode", "unsupported"),
            "output": "CardPaymentNoticeCandidate",
        }

    @application.post(
        "/v1/analyze/card-payment-notice",
        response_model=CardPaymentNoticeCandidate,
        tags=["analyzer"],
    )
    def analyze(artifact: SemanticInput) -> CardPaymentNoticeCandidate:
        # Sync endpoint: blocking provider calls run in FastAPI's worker threadpool.
        return service.analyze_card_payment_notice(artifact)

    return application


app = create_app()
