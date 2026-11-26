# NEXORA quality gates. Every target is a one-line call into tools/nx.py, the single source
# of truth (Windows workstations without `make` run: python tools/nx.py <target>).
# CI runs these exact targets.

PY ?= $(shell command -v python3 2>/dev/null || command -v python)
NX := $(PY) tools/nx.py

.DEFAULT_GOAL := help
.PHONY: help setup lock lint format typecheck test test-unit test-contract test-integration \
        validate build docker-build security-check openapi-update check

help: ## Show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

setup: ## Create .venv from the pinned lock, install web deps
	@$(NX) setup

lock: ## Re-resolve requirements/*.txt with hashes
	@$(NX) lock

lint: ## ruff (python) + eslint/prettier (web)
	@$(NX) lint

format: ## Auto-format python and web sources
	@$(NX) format

typecheck: ## mypy --strict + tsc
	@$(NX) typecheck

test: ## unit + contract tests
	@$(NX) test

test-unit: ## unit tests with coverage gate
	@$(NX) test-unit

test-contract: ## OpenAPI snapshot, SDK<->API, adapter port contracts
	@$(NX) test-contract

test-integration: ## tests needing real services (PostgreSQL via NEXORA_TEST_DATABASE_URL)
	@$(NX) test-integration

validate: ## architecture boundaries, repo policy, YAML, deploy config
	@$(NX) validate

build: ## python wheels + web bundle (no Docker)
	@$(NX) build

docker-build: ## container images (needs Docker daemon; always run in CI)
	@$(NX) docker-build

security-check: ## bandit, pip-audit, npm audit, secret scan
	@$(NX) security-check

openapi-update: ## regenerate contracts/openapi from code
	@$(NX) openapi-update

check: ## everything a pull request must pass
	@$(NX) check
