"""Environment-driven configuration base.

Rules (see docs/engineering/conventions.md):
* configuration comes ONLY from environment variables (12-factor) -- never from files
  checked into the repository and never from workstation paths;
* secrets are `SecretStr` and are never logged or serialised;
* there are no defaults that point at a developer machine (no localhost fallbacks for
  anything except values explicitly marked as development-only in the settings class).
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class BaseServiceSettings(BaseSettings):
    """Common settings for every NEXORA service. Env prefix: ``NEXORA_``."""

    model_config = SettingsConfigDict(
        env_prefix="NEXORA_",
        extra="ignore",
        case_sensitive=False,
        frozen=True,
    )

    environment: Environment = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_json: bool = True
