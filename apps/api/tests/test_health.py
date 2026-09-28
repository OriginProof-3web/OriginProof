from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain import JsonRpcBlockchainReader
from originproof_api.main import (
    UnavailableBlockchainReader,
    configured_blockchain_reader,
    create_app,
)
from originproof_api.settings import Settings
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


def test_incomplete_chain_configuration_is_unavailable() -> None:
    reader = configured_blockchain_reader(
        Settings(database_url="sqlite+aiosqlite://", blockchain_rpc_url="http://127.0.0.1:8545")
    )

    assert isinstance(reader, UnavailableBlockchainReader)


def test_complete_chain_configuration_selects_reader(tmp_path) -> None:
    manifest = tmp_path / "31337.local.json"
    manifest.write_text(
        '{"chain_id":31337,"deployment_block":1,"contracts":'
        '{"IssuerRegistry":{"address":"0x1111111111111111111111111111111111111111"},'
        '"IssuerKeyRegistry":{"address":"0x2222222222222222222222222222222222222222"}}}'
    )

    reader = configured_blockchain_reader(
        Settings(
            database_url="sqlite+aiosqlite://",
            blockchain_rpc_url="http://127.0.0.1:8545",
            blockchain_manifest_path=str(manifest),
        )
    )

    assert isinstance(reader, JsonRpcBlockchainReader)


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
