from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnalyzerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=None, hide_input_in_errors=True)

    llm_provider: Literal["mock", "openai"] = "mock"
    openai_model: str = Field(default="gpt-5.6-luna", min_length=1, pattern=r"^\S+$")
    openai_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    llm_timeout_seconds: float = Field(default=20, gt=0, allow_inf_nan=False)
    llm_max_retries: int = Field(default=2, ge=0, le=2)
    analyzer_min_confidence: float = Field(default=0.70, ge=0, le=1)
