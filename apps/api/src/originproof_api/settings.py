from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets are loaded from the environment and never logged."""

    database_url: str = "postgresql+asyncpg://originproof:originproof@postgres:5432/originproof"
    blockchain_rpc_url: str | None = None
    blockchain_manifest_path: str | None = None
    blockchain_issuer_id: str = "iss_origin_mock_bank"
    blockchain_chain_id: int = 31337
    session_cookie_secure: bool = False
    finals_payment_issuer_id: str = "iss_origin_mock_bank"
    finals_document_issuer_id: str = "iss_origin_mock_office"
    finals_document_institution_code: str = "ORIGIN_MOCK_OFFICE"
    signer_directory: str = "build/secrets/issuer-signers"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="API_",
        extra="ignore",
    )
