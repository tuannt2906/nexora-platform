"""Control Plane configuration. Environment variables only (prefix ``NEXORA_``)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import NoDecode

from nexora_core.settings import BaseServiceSettings


class Settings(BaseServiceSettings):
    # Secrets: no defaults on purpose. A missing secret must stop the process at startup
    # instead of silently running with a guessable value.
    database_url: SecretStr
    api_token: SecretStr

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    git_sha: str = "unknown"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("api_token")
    @classmethod
    def _token_strength(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 24:
            raise ValueError("NEXORA_API_TOKEN must be at least 24 characters")
        return value

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production"
