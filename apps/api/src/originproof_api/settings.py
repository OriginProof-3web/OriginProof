from __future__ import annotations

from infrastructure.blockchain.network import CHAIN_TARGETS, chain_target, rpc_urls
from originproof_core.wallet_contract import Address
from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets are loaded from the environment and never logged."""

    database_url: str = "postgresql+asyncpg://originproof:originproof@postgres:5432/originproof"
    # One switch (CHAIN_TARGET=anvil|sepolia) selects chain ID, wallet manifest and RPC rules.
    chain_target: str = Field(
        default="anvil", validation_alias=AliasChoices("CHAIN_TARGET", "chain_target")
    )
    blockchain_rpc_url: str | None = Field(default=None, repr=False)
    blockchain_rpc_fallback_url: str | None = Field(default=None, repr=False)
    blockchain_manifest_path: str | None = None
    wallet_manifest_path: str | None = None
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
    wallet_registry_address: Address | None = None
    wallet_operator_addresses: dict[str, Address] = {}
    wallet_internal_approvers: dict[str, str] = {}
    wallet_demo_email_enabled: bool = False
    wallet_email_secret: SecretStr | None = Field(default=None, repr=False, exclude=True)
    wallet_text_input_enabled: bool = False
    wallet_image_input_enabled: bool = False
    signup_enabled: bool = False
    wallet_relay_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="API_",
        extra="ignore",
        # Startup errors must not echo inputs such as provider-keyed RPC URLs.
        hide_input_in_errors=True,
    )

    @field_validator("chain_target")
    @classmethod
    def _known_chain_target(cls, value: str) -> str:
        return chain_target(value).name

    @model_validator(mode="after")
    def _select_chain(self):
        target = CHAIN_TARGETS[self.chain_target]
        if (
            "blockchain_chain_id" in self.model_fields_set
            and self.blockchain_chain_id != target.chain_id
        ):
            raise ValueError(f"API_BLOCKCHAIN_CHAIN_ID conflicts with CHAIN_TARGET={target.name}")
        self.blockchain_chain_id = target.chain_id
        self.wallet_manifest_path = self.wallet_manifest_path or str(target.wallet_manifest_path)
        if target.name == "sepolia" or self.blockchain_rpc_url or self.blockchain_rpc_fallback_url:
            rpc_urls(target, self.blockchain_rpc_url, self.blockchain_rpc_fallback_url)
        return self

    @property
    def blockchain_rpc_urls(self) -> tuple[str, ...]:
        """Primary then fallback. Reader/projection reads fail over; writes use the primary only."""
        if not self.blockchain_rpc_url:
            return ()
        target = CHAIN_TARGETS[self.chain_target]
        return rpc_urls(target, self.blockchain_rpc_url, self.blockchain_rpc_fallback_url)
