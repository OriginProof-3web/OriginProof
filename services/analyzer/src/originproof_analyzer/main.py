from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from originproof_core import CardPaymentNotice, CardPaymentNoticeCandidate

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
        responses={
            200: {
                "headers": {
                    name: {"description": description, "schema": {"type": "string"}}
                    for name, description in {
                        "X-OriginProof-Candidate-Source": "ai or mock; never user-confirmed.",
                        "X-OriginProof-Confirmation-Required": (
                            "Always true, even at high confidence."
                        ),
                        "X-OriginProof-Artifact-Comparison": "Always not-performed.",
                        "X-OriginProof-Missing-Comparison-Fields": (
                            "Comma-separated null CardPaymentNotice payload fields, or none. "
                            "none does not establish correct values or complete artifact matching."
                        ),
                    }.items()
                }
            }
        },
    )
    def analyze(artifact: SemanticInput, response: Response) -> CardPaymentNoticeCandidate:
        # Sync endpoint: blocking provider calls run in FastAPI's worker threadpool.
        candidate = service.analyze_card_payment_notice(artifact)
        # Schema validity/confidence do not ground values in the artifact. These headers
        # describe extraction; consumers still need to enforce confirmation before comparison.
        response.headers["X-OriginProof-Candidate-Source"] = (
            "mock" if service.provider.provider_name == "mock" else "ai"
        )
        response.headers["X-OriginProof-Confirmation-Required"] = "true"
        response.headers["X-OriginProof-Artifact-Comparison"] = "not-performed"
        response.headers["X-OriginProof-Missing-Comparison-Fields"] = ",".join(
            name for name in CardPaymentNotice.model_fields if getattr(candidate, name) is None
        ) or "none"
        return candidate

    return application


app = create_app()
