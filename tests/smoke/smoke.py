#!/usr/bin/env python3
"""Deployment smoke test for a running NEXORA stack. Standard library only.

    NEXORA_API_TOKEN=... python tests/smoke/smoke.py --base-url http://127.0.0.1:8080 \
        --token-env NEXORA_API_TOKEN [--wait-seconds 60]

It proves that a deployment is *wired* correctly (liveness, readiness incl. database, authentication
enforced, authenticated API reachable, and metrics when --metrics-url is given: /metrics is
deliberately NOT exposed through the web tier). It does NOT prove production readiness:
see docs/operations/runbook-smoke.md for what else must be checked.

Exit codes: 0 all checks passed, 1 at least one check failed, 2 usage/configuration error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

REQUEST_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


def http_get(url: str, token: str | None = None) -> Response:
    """GET ``url``. Non-2xx statuses are returned, not raised; transport errors propagate."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"unsupported URL scheme: {url}")
    request = urllib.request.Request(url, method="GET")  # noqa: S310 - scheme validated above
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as resp:  # noqa: S310
            return Response(resp.status, resp.read())
    except urllib.error.HTTPError as exc:
        return Response(exc.code, exc.read())


@dataclass(frozen=True)
class Check:
    name: str
    run: Callable[[str, str], str | None]  # (base_url, token) -> None if OK else failure reason


def _expect_status(path: str, expected: int, *, auth: bool) -> Callable[[str, str], str | None]:
    def run(base_url: str, token: str) -> str | None:
        response = http_get(base_url + path, token if auth else None)
        if response.status != expected:
            return f"GET {path} -> HTTP {response.status}, expected {expected}"
        return None

    return run


def _readyz(base_url: str, _token: str) -> str | None:
    response = http_get(base_url + "/readyz")
    if response.status != 200:
        return f"GET /readyz -> HTTP {response.status}, expected 200"
    try:
        body = json.loads(response.body)
    except ValueError:
        # e.g. the SPA fallback page answering instead of the API: that is NOT a readiness proof
        return "GET /readyz did not return the API JSON (is the route proxied to the API?)"
    if not isinstance(body, dict) or body.get("status") != "ready":
        return f"GET /readyz reported {body!r}, expected status 'ready'"
    return None


def metrics_check(metrics_url: str) -> Check:
    def run(_base_url: str, _token: str) -> str | None:
        response = http_get(metrics_url)
        if response.status != 200:
            return f"GET {metrics_url} -> HTTP {response.status}, expected 200"
        if b"# HELP" not in response.body:
            return f"GET {metrics_url} did not return Prometheus exposition text"
        return None

    return Check("metrics   (direct, --metrics-url)", run)


def _platform(base_url: str, token: str) -> str | None:
    response = http_get(base_url + "/api/v1/platform", token)
    if response.status != 200:
        return f"GET /api/v1/platform (authenticated) -> HTTP {response.status}, expected 200"
    try:
        body = json.loads(response.body)
    except ValueError:
        return "GET /api/v1/platform did not return JSON"
    if not isinstance(body, dict) or "version" not in body:
        return "GET /api/v1/platform JSON has no 'version' field"
    return None


CHECKS: tuple[Check, ...] = (
    Check("liveness  /healthz", _expect_status("/healthz", 200, auth=False)),
    Check("readiness /readyz (database reachable)", _readyz),
    Check(
        "auth enforced: /api/v1/platform without token -> 401",
        _expect_status("/api/v1/platform", 401, auth=False),
    ),
    Check("authenticated /api/v1/platform", _platform),
)


def wait_until_ready(base_url: str, seconds: float) -> None:
    """Poll /readyz until it answers 200 or the budget is exhausted (no sleep when 0)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if http_get(base_url + "/readyz").status == 200:
                return
        except OSError:
            pass
        time.sleep(2)


def run_checks(
    base_url: str, token: str, metrics_url: str | None = None
) -> list[tuple[str, str | None]]:
    results: list[tuple[str, str | None]] = []
    checks = (*CHECKS, metrics_check(metrics_url)) if metrics_url else CHECKS
    for check in checks:
        try:
            problem = check.run(base_url, token)
        except (OSError, ValueError) as exc:
            problem = f"{type(exc).__name__}: {exc}"
        results.append((check.name, problem))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--base-url", required=True, help="e.g. https://nexora.example.com")
    parser.add_argument("--token-env", default="NEXORA_API_TOKEN", help="env var holding the token")
    parser.add_argument("--wait-seconds", type=float, default=0.0, help="wait for /readyz first")
    parser.add_argument(
        "--metrics-url",
        default=None,
        help="full URL of /metrics reached directly (not exposed through the web tier)",
    )
    args = parser.parse_args(argv)

    token = os.environ.get(args.token_env, "")
    if not token:
        sys.stderr.write(f"error: environment variable {args.token_env} is empty or unset\n")
        return 2
    base_url = args.base_url.rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        sys.stderr.write("error: --base-url must start with http:// or https://\n")
        return 2

    if args.wait_seconds > 0:
        wait_until_ready(base_url, args.wait_seconds)

    failures = 0
    results = run_checks(base_url, token, args.metrics_url)
    if not args.metrics_url:
        sys.stdout.write("SKIP  metrics (not exposed via the web tier; pass --metrics-url)\n")
    for name, problem in results:
        if problem is None:
            sys.stdout.write(f"PASS  {name}\n")
        else:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n        {problem}\n")
    sys.stdout.write(f"\n{len(results) - failures}/{len(results)} smoke checks passed\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
