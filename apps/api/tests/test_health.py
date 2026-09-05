from httpx import ASGITransport, AsyncClient
from originproof_api.main import app
from originproof_core import CardPaymentNoticeCandidate, VerificationRequest


async def test_live_healthcheck() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


async def test_verification_is_inconclusive_without_configured_adapters() -> None:
    request = VerificationRequest(
        proof_id="prf_demo_001",
        candidate=CardPaymentNoticeCandidate(confidence=0.99),
        request_id="req_test_001",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/mvp/card-notices/verify",
            json=request.model_dump(mode="json"),
        )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "INCONCLUSIVE"
    assert response.json()["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
