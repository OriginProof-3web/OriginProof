import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from infrastructure.blockchain import JsonRpcBlockchainReader
from originproof_api.main import (
    UnavailableBlockchainReader,
    configured_blockchain_reader,
    create_app,
)
from originproof_api.readiness import REVISION, check_ready
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


@pytest.mark.parametrize("collision", [False, True])
async def test_readiness_rejects_legacy_pre_registered_issuer_collision(
    tmp_path, monkeypatch, collision
):
    settings = Settings(
        _env_file=None,
        signer_directory=str(tmp_path / "signers"),
        finals_payment_issuer_id="iss_origin_mock_bank" if collision else "iss_finals_mock_bank",
        finals_document_issuer_id="iss_finals_mock_office",
    )
    rows = [
        SimpleNamespace(role=role, issuer_id=issuer)
        for role, issuer in (
            ("operator", None),
            ("recipient", None),
            ("issuer", settings.finals_payment_issuer_id),
            ("issuer", settings.finals_document_issuer_id),
        )
    ]
    db = AsyncMock()
    db.scalar.return_value = REVISION
    db.scalars.return_value = rows
    session = AsyncMock()
    session.__aenter__.return_value = db
    reader = SimpleNamespace(get_issuer=AsyncMock())
    monkeypatch.setattr("originproof_api.main.configured_blockchain_reader", lambda _: reader)
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=settings,
            database=SimpleNamespace(ping=AsyncMock(), session_factory=lambda: session),
            analysis_worker_error=None,
        )
    )
    if collision:
        with pytest.raises(HTTPException) as error:
            await check_ready(app)
        assert (error.value.status_code, error.value.detail) == (503, "RUNTIME_NOT_READY")
        reader.get_issuer.assert_not_awaited()
    else:
        await check_ready(app)
        reader.get_issuer.assert_awaited_once_with(settings.blockchain_issuer_id)


def test_incomplete_chain_configuration_is_unavailable() -> None:
    reader = configured_blockchain_reader(
        Settings(database_url="sqlite+aiosqlite://", blockchain_rpc_url="http://127.0.0.1:8545")
    )

    assert isinstance(reader, UnavailableBlockchainReader)


def test_complete_chain_configuration_selects_reader(tmp_path) -> None:
    manifest = tmp_path / "31337.local.json"
    manifest.write_text(
        json.dumps(
            {
                "chain_id": 31337,
                "genesis_block_hash": "0x" + "a" * 64,
                "deployment_id": "dep_" + "b" * 64,
                "deployment_block": 1,
                "deployment_block_hash": "0x" + "c" * 64,
                "source_commit_sha": "d" * 40,
                "contracts": {
                    "IssuerRegistry": {
                        "address": "0x" + "11" * 20,
                        "constructor_arguments": ["0x" + "33" * 20],
                        "abi_sha256": "1" * 64,
                    },
                    "IssuerKeyRegistry": {
                        "address": "0x" + "22" * 20,
                        "constructor_arguments": ["0x" + "33" * 20, "0x" + "11" * 20],
                        "abi_sha256": "2" * 64,
                    },
                },
                "roles": {
                    "registry_admin": "0x" + "33" * 20,
                    "issuer_manager": "0x" + "44" * 20,
                    "key_manager": "0x" + "55" * 20,
                    "issuer_account": "0x" + "66" * 20,
                },
            }
        )
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
