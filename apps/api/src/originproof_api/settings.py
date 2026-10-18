from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets are loaded from the environment and never logged."""

    database_url: str = "postgresql+asyncpg://originproof:originproof@postgres:5432/originproof"
    blockchain_rpc_url: str | None = None
    blockchain_manifest_path: str | None = None
    blockchain_issuer_id: str = "iss_origin_mock_bank"
    blockchain_chain_id: int = 31337
    projection_enabled: bool = False
    projection_poll_seconds: int = Field(default=5, ge=1, le=60)
    session_cookie_secure: bool = False
    finals_payment_issuer_id: str = "iss_origin_mock_bank"
    finals_document_issuer_id: str = "iss_origin_mock_office"
    finals_document_institution_code: str = "ORIGIN_MOCK_OFFICE"
    signer_directory: str = "build/secrets/issuer-signers"
    browser_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    request_body_max_bytes: int = Field(default=65536, ge=1024, le=1048576)
    request_body_timeout_seconds: int = Field(default=10, ge=1, le=60)
    requests_per_minute: int = Field(default=120, ge=1)
    logins_per_minute: int = Field(default=10, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="API_",
        extra="ignore",
    )
