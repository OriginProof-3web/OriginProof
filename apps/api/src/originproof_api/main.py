import re
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from infrastructure.blockchain import JsonRpcBlockchainReader
from originproof_core import (
    BlockchainReader,
    DependencyUnavailableError,
    VerificationRequest,
    VerificationResult,
    VerificationService,
)
from originproof_core.ports import IssuerRecord, KeyRecord

from .accounts import router as auth_router
from .applications import router as applications_router
from .chain_management import router as chain_router
from .database import Database
from .finals_proofs import router as finals_router
from .operations import router as operations_router
from .repositories import SqlAlchemyProofRepository
from .settings import Settings


class UnavailableBlockchainReader(BlockchainReader):
    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None:
        raise DependencyUnavailableError("blockchain reader is not configured")

    async def get_key(self, key_id: str) -> KeyRecord | None:
        raise DependencyUnavailableError("blockchain reader is not configured")

    async def is_key_valid(self, key_id: str, at: datetime) -> bool:
        raise DependencyUnavailableError("blockchain reader is not configured")


def configured_blockchain_reader(settings: Settings) -> BlockchainReader:
    if not settings.blockchain_rpc_url or not settings.blockchain_manifest_path:
        return UnavailableBlockchainReader()
    try:
        return JsonRpcBlockchainReader(
            settings.blockchain_rpc_url,
            settings.blockchain_manifest_path,
            issuer_ids=[settings.blockchain_issuer_id],
            expected_chain_id=settings.blockchain_chain_id,
        )
    except DependencyUnavailableError:
        return UnavailableBlockchainReader()


def _request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID")
    if supplied is not None and re.fullmatch(r"req_[A-Za-z0-9_-]+", supplied):
        return supplied
    return f"req_{uuid4().hex}"


def create_app(
    verification_service: VerificationService | None = None,
    database: Database | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    app_database = database or Database(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await app_database.dispose()

    app = FastAPI(title="OriginProof API", version="0.1.0", lifespan=lifespan)
    app.state.database = app_database
    app.state.settings = app_settings
    app.include_router(auth_router)
    app.include_router(applications_router)
    app.include_router(operations_router)
    app.include_router(chain_router)
    app.include_router(finals_router)
    app.state.verification_service = verification_service or VerificationService(
        SqlAlchemyProofRepository(app_database.session_factory),
        configured_blockchain_reader(app_settings),
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        return JSONResponse(
            status_code=422,
            content={"error": "MALFORMED_INPUT", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", tags=["health"])
    async def ready() -> dict[str, str]:
        await app.state.database.ping()
        return {"status": "ready"}

    @app.post(
        "/v1/mvp/card-notices/verify",
        response_model=VerificationResult,
        tags=["verification"],
    )
    async def verify_card_payment_notice(
        request: VerificationRequest, response: Response
    ) -> VerificationResult:
        response.headers["X-Request-ID"] = request.request_id
        return await app.state.verification_service.verify(request)

    return app


app = create_app()
