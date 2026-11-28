"""Verifies tests/smoke/smoke.py itself against a tiny fake NEXORA server."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

TOKEN = "unit-test-token"


def _load_smoke() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "tests" / "smoke" / "smoke.py"
    spec = importlib.util.spec_from_file_location("nexora_smoke", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve string annotations through sys.modules
    spec.loader.exec_module(module)
    return module


smoke = _load_smoke()


def _handler(
    *, ready: bool = True, enforce_auth: bool = True, html_readyz: bool = False
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._send(200, b'{"status":"ok"}')
            elif self.path == "/readyz":
                if html_readyz:  # what the web tier's SPA fallback would answer
                    self._send(200, b"<html>app</html>", "text/html")
                else:
                    self._send(200 if ready else 503, b'{"status":"ready"}')
            elif self.path == "/metrics":
                self._send(200, b"# HELP up test\n# TYPE up gauge\nup 1\n", "text/plain")
            elif self.path == "/api/v1/platform":
                authed = self.headers.get("Authorization") == f"Bearer {TOKEN}"
                if enforce_auth and not authed:
                    self._send(401, b'{"detail":"unauthorized"}')
                else:
                    self._send(200, json.dumps({"version": "0.0.0"}).encode())
            else:
                self._send(404, b"{}")

    return Handler


@contextmanager
def _server(**kwargs: bool) -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler(**kwargs))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_all_checks_pass_against_healthy_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    with _server() as url:
        code = smoke.main(["--base-url", url, "--token-env", "SMOKE_TOKEN"])
    out = capsys.readouterr().out
    assert code == 0
    assert "4/4 smoke checks passed" in out
    assert "SKIP  metrics" in out


def test_fails_when_not_ready(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    with _server(ready=False) as url:
        code = smoke.main(["--base-url", url, "--token-env", "SMOKE_TOKEN"])
    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL  readiness" in out


def test_fails_when_auth_is_not_enforced(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    with _server(enforce_auth=False) as url:
        code = smoke.main(["--base-url", url, "--token-env", "SMOKE_TOKEN"])
    assert code == 1
    assert "FAIL  auth enforced" in capsys.readouterr().out


def test_fails_with_wrong_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", "wrong")
    with _server() as url:
        code = smoke.main(["--base-url", url, "--token-env", "SMOKE_TOKEN"])
    assert code == 1
    assert "FAIL  authenticated" in capsys.readouterr().out


def test_unreachable_server_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    code = smoke.main(["--base-url", "http://127.0.0.1:1", "--token-env", "SMOKE_TOKEN"])
    assert code == 1
    assert "0/4 smoke checks passed" in capsys.readouterr().out


def test_missing_token_is_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SMOKE_TOKEN", raising=False)
    assert smoke.main(["--base-url", "http://127.0.0.1:1", "--token-env", "SMOKE_TOKEN"]) == 2
    assert "SMOKE_TOKEN" in capsys.readouterr().err


def test_bad_url_scheme_is_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    assert smoke.main(["--base-url", "ftp://example.com", "--token-env", "SMOKE_TOKEN"]) == 2


def test_wait_until_ready_returns_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    with _server() as url:
        smoke.wait_until_ready(url, 5)  # must return promptly, not exhaust the budget


def test_metrics_checked_when_url_given(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    with _server() as url:
        code = smoke.main(
            ["--base-url", url, "--token-env", "SMOKE_TOKEN", "--metrics-url", url + "/metrics"]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "5/5 smoke checks passed" in out
        code = smoke.main(
            ["--base-url", url, "--token-env", "SMOKE_TOKEN", "--metrics-url", url + "/nope"]
        )
    assert code == 1
    assert "FAIL  metrics" in capsys.readouterr().out


def test_html_instead_of_api_readiness_is_not_a_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SMOKE_TOKEN", TOKEN)
    with _server(html_readyz=True) as url:
        code = smoke.main(["--base-url", url, "--token-env", "SMOKE_TOKEN"])
    assert code == 1
    assert "did not return the API JSON" in capsys.readouterr().out
