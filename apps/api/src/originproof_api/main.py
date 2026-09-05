from datetime import datetime

from fastapi import FastAPI
from originproof_core import (
    BlockchainReader,
    DependencyUnavailableError,
    ProofRepository,
    VerificationRequest,
    VerificationResult,
    VerificationService,
)
from originproof_core.ports import IssuerRecord, KeyRecord


class UnavailableProofRepository(ProofRepository):
    async def get_proof(self, proof_id: str):
        raise DependencyUnavailableError("signed-proof repository is not configured")


class UnavailableBlockchainReader(BlockchainReader):
    async def get_issuer(self, issuer_id: str) -> IssuerRecord | None:
        raise DependencyUnavailableError("blockchain reader is not configured")

    async def get_key(self, key_id: str) -> KeyRecord | None:
        raise DependencyUnavailableError("blockchain reader is not configured")

    async def is_key_valid(self, key_id: str, at: datetime) -> bool:
        raise DependencyUnavailableError("blockchain reader is not configured")


def create_app(verification_service: VerificationService | None = None) -> FastAPI:
    app = FastAPI(title="OriginProof API", version="0.1.0")
    app.state.verification_service = verification_service or VerificationService(
        UnavailableProofRepository(), UnavailableBlockchainReader()
    )

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", tags=["health"])
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.post(
        "/v1/verifications/card-payment-notice",
        response_model=VerificationResult,
        tags=["verification"],
    )
    async def verify_card_payment_notice(request: VerificationRequest) -> VerificationResult:
        return await app.state.verification_service.verify(request)

    return app


app = create_app()
