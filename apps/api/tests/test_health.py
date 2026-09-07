from httpx import ASGITransport, AsyncClient
from originproof_api.main import UnavailableBlockchainReader, create_app
from originproof_core import (
    CardPaymentNoticeCandidate,
    DependencyUnavailableError,
    VerificationRequest,
    VerificationService,
)


class UnavailableProofRepository:
    async def get_proof(self, proof_id: str):
        raise DependencyUnavailableError("proof repository is not configured")


async def test_live_healthcheck() -> None:
    test_app = create_app(
        VerificationService(UnavailableProofRepository(), UnavailableBlockchainReader())
    )
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


async def test_test_page_returns_html() -> None:
    test_app = create_app(
        VerificationService(UnavailableProofRepository(), UnavailableBlockchainReader())
    )
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/test")

    assert response.status_code == 200
    assert "OriginProof 테스트 페이지" in response.text


async def test_verification_is_inconclusive_without_configured_adapters() -> None:
    request = VerificationRequest(
        proof_id="prf_demo_001",
        candidate=CardPaymentNoticeCandidate(confidence=0.99),
        request_id="req_test_001",
    )
    test_app = create_app(
        VerificationService(UnavailableProofRepository(), UnavailableBlockchainReader())
    )
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(
            "/v1/mvp/card-notices/verify",
            json=request.model_dump(mode="json"),
        )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "INCONCLUSIVE"
    assert response.json()["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
    assert response.headers["X-Request-ID"] == "req_test_001"


async def test_malformed_request_has_safe_error_body() -> None:
    test_app = create_app(
        VerificationService(UnavailableProofRepository(), UnavailableBlockchainReader())
    )
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(
            "/v1/mvp/card-notices/verify",
            json={"proof_id": "not-a-proof"},
            headers={"X-Request-ID": "req_safe_error_001"},
        )

    assert response.status_code == 422
    assert response.json() == {"error": "MALFORMED_INPUT", "request_id": "req_safe_error_001"}
    assert response.headers["X-Request-ID"] == "req_safe_error_001"
