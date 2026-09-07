from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets are loaded from the environment and never logged."""

    database_url: str = "postgresql+asyncpg://originproof:originproof@postgres:5432/originproof"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="API_",
        extra="ignore",
    )
