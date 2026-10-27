import asyncio
import re
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from infrastructure.blockchain import JsonRpcBlockchainReader
from infrastructure.blockchain.wallet_deployment import WalletRegistryConnector
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
from .chain_network import router as chain_network_router
from .database import Database
from .finals_proofs import router as finals_router
from .operations import router as operations_router
from .projection import SyncView, run_projection
from .projection import router as projection_router
from .repositories import SqlAlchemyProofRepository
from .security import RequestSecurity
from .settings import Settings
from .wallet_analyses import cleanup, launch, maintenance
from .wallet_analyses import router as wallet_analyses_router
from .wallet_documents import router as wallet_documents_router
from .wallet_governance import router as wallet_governance_router
from .wallet_onboarding import router as wallet_onboarding_router
from .wallet_runtime import WalletRuntime


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
        # CHAIN_TARGET picks chain ID and RPC rules; reads fail over primary -> fallback.
        return JsonRpcBlockchainReader(
            settings.blockchain_rpc_urls,
            settings.blockchain_manifest_path,
            issuer_ids=[settings.blockchain_issuer_id],
            expected_chain_id=settings.blockchain_chain_id,
        )
    except DependencyUnavailableError:
        return UnavailableBlockchainReader()


def _request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID")
    if supplied is not None and re.fullmatch(r"req_[A-Za-z0-9_-]{1,124}", supplied):
        return supplied
    return f"req_{uuid4().hex}"


def create_app(
    verification_service: VerificationService | None = None,
    database: Database | None = None,
    settings: Settings | None = None,
    wallet_chain=None,
    analysis_processor=None,
) -> FastAPI:
    app_settings = settings or Settings()
    app_database = database or Database(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        stop = asyncio.Event()
        wallet_enabled = (
            app_settings.wallet_registry_address
            or app_settings.wallet_text_input_enabled
            or app_settings.wallet_demo_email_enabled
        )
        task = maintenance_task = wallet_client = None
        try:
            # 지갑 Registry 생산 연결: 주입된 chain 이 없고 주소·RPC 가 있을 때만.
            # 배포 기록(manifest)으로 체인 위 배포를 검증한 뒤에만 연결한다.
            runtime = app.state.wallet_runtime
            if (
                runtime.chain is None
                and app_settings.wallet_registry_address
                and app_settings.blockchain_rpc_urls
            ):
                wallet_client = httpx.AsyncClient(timeout=10, trust_env=False)
                runtime.connect = WalletRegistryConnector(wallet_client, app_settings)
                runtime.chain = await runtime.connect()
            if wallet_enabled:
                for analysis_id in await cleanup(app, restart=True):
                    launch(app, analysis_id)
                maintenance_task = asyncio.create_task(maintenance(app, stop))
            if app_settings.projection_enabled:
                task = asyncio.create_task(run_projection(app, stop))
            yield
        finally:
            stop.set()
            if task:
                await task
            if maintenance_task:
                await maintenance_task
            pending = list(app.state.analysis_tasks)
            for worker in pending:
                worker.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            await app_database.dispose()
            if wallet_client is not None:
                await wallet_client.aclose()

    app = FastAPI(
        title="OriginProof API",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            413: {"description": "REQUEST_TOO_LARGE: request body exceeds configured limit"},
            429: {"description": "RATE_LIMITED: retry after Retry-After seconds"},
        },
    )
    app.add_middleware(RequestSecurity, settings=app_settings)
    app.state.database = app_database
    app.state.settings = app_settings
    app.state.wallet_runtime = WalletRuntime(app_database, app_settings, wallet_chain)
    app.state.analysis_processor = analysis_processor
    app.state.analysis_tasks = set()
    app.state.analysis_worker_error = None
    app.state.projection = SyncView(
        status="STARTING" if app_settings.projection_enabled else "DISABLED"
    )
    app.include_router(projection_router)
    app.include_router(auth_router)
    app.include_router(applications_router)
    app.include_router(operations_router)
    app.include_router(chain_router)
    app.include_router(chain_network_router)
    app.include_router(finals_router)
    app.include_router(wallet_onboarding_router)
    app.include_router(wallet_governance_router)
    app.include_router(wallet_documents_router)
    app.include_router(wallet_analyses_router)
    app.state.verification_service = verification_service or VerificationService(
        SqlAlchemyProofRepository(app_database.session_factory),
        configured_blockchain_reader(app_settings),
    )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        if request.url.path.startswith("/v3/"):
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "MALFORMED_INPUT",
                    "request_id": request_id,
                    "field_paths": [".".join(str(x) for x in e["loc"][1:]) for e in error.errors()],
                },
                headers={"X-Request-ID": request_id},
            )
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
        from .readiness import check_ready

        await check_ready(app)
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
