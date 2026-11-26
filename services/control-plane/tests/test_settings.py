from __future__ import annotations

import pytest
from pydantic import ValidationError

from nexora_control_plane.settings import Settings


def test_secrets_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXORA_DATABASE_URL", raising=False)
    monkeypatch.delenv("NEXORA_API_TOKEN", raising=False)
    with pytest.raises(ValidationError) as err:
        Settings()  # type: ignore[call-arg]
    assert {e["loc"][0] for e in err.value.errors()} == {"database_url", "api_token"}


def test_short_token_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXORA_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("NEXORA_API_TOKEN", "short")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_env_parsing_and_secret_masking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXORA_DATABASE_URL", "postgresql+psycopg://u:pw@db/nexora")
    monkeypatch.setenv("NEXORA_API_TOKEN", "a" * 24)
    monkeypatch.setenv("NEXORA_CORS_ORIGINS", "https://a.example, https://b.example,")
    monkeypatch.setenv("NEXORA_ENVIRONMENT", "production")
    settings = Settings()  # type: ignore[call-arg]
    assert settings.cors_origins == ["https://a.example", "https://b.example"]
    assert settings.docs_enabled is False
    assert "pw" not in repr(settings)
    assert "pw" not in settings.model_dump_json()
