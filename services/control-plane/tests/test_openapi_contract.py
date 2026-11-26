from __future__ import annotations

from pathlib import Path

import pytest

from nexora_control_plane.openapi import render

SNAPSHOT = Path(__file__).resolve().parents[3] / "contracts" / "openapi" / "control-plane.v1.json"


@pytest.mark.contract
def test_openapi_snapshot_is_current() -> None:
    """The committed OpenAPI contract must equal what the code produces.

    Intentional API change? Run `python tools/nx.py openapi-update` and commit the diff.
    """
    assert SNAPSHOT.exists(), "run: python tools/nx.py openapi-update"
    assert SNAPSHOT.read_text(encoding="utf-8") == render()
