from __future__ import annotations

import io
import json
from collections.abc import Callable
from contextlib import redirect_stdout

import pytest

from nexora_core.errors import ConfigurationError, NexoraError, NotFoundError
from nexora_core.logging import configure_logging, get_logger
from nexora_core.modules import CriterionStatus, load_module_specs, parse_module_spec
from nexora_core.settings import BaseServiceSettings

VALID = """
id = "demo"
title = "Demo"
maturity = "contract"
summary = "s"
responsibilities = ["r"]
public_interfaces = ["pkg.mod.Port"]
engines = ["kafka"]

[[config]]
key = "NEXORA_DEMO_URL"
description = "d"

[[acceptance]]
id = "DEM-1"
criterion = "c"
status = "planned"
"""


def test_error_codes_are_stable_and_carry_details() -> None:
    err = NotFoundError("nope", details={"id": 1})
    assert isinstance(err, NexoraError)
    assert (err.code, err.message, err.details) == ("not_found", "nope", {"id": 1})


def test_base_settings_read_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXORA_ENVIRONMENT", "staging")
    monkeypatch.setenv("NEXORA_LOG_LEVEL", "DEBUG")
    settings = BaseServiceSettings()
    assert (settings.environment, settings.log_level, settings.log_json) == (
        "staging",
        "DEBUG",
        True,
    )


def test_json_logging_emits_one_json_object_per_event() -> None:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        configure_logging("INFO", json_output=True)  # binds the logger to the patched stdout
        get_logger("t").info("hello", answer=42)
    record = json.loads(buffer.getvalue().strip())
    assert record["event"] == "hello"
    assert record["answer"] == 42
    assert record["level"] == "info"
    assert record["timestamp"].endswith("Z")


def test_module_spec_parsing() -> None:
    spec = parse_module_spec(VALID)
    assert spec.id == "demo"
    assert spec.acceptance[0].status is CriterionStatus.PLANNED


@pytest.mark.parametrize(
    "mutation",
    [
        lambda t: t.replace('id = "demo"', 'id = "Bad Id"'),
        lambda t: t.replace('"kafka"', '"not-an-engine"'),
        lambda t: t.replace("NEXORA_DEMO_URL", "demo_url"),
        lambda t: t.replace('status = "planned"', 'status = "done"'),
        lambda t: t + "\n= broken toml",
    ],
)
def test_invalid_module_spec_is_rejected(mutation: Callable[[str], str]) -> None:
    with pytest.raises(ConfigurationError):
        parse_module_spec(mutation(VALID))


def test_loader_rejects_unknown_module_package() -> None:
    with pytest.raises(ModuleNotFoundError):
        load_module_specs("nexora_modules", ("does_not_exist",))
