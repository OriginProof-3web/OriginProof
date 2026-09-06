SHELL := /bin/sh

.DEFAULT_GOAL := help

.PHONY: help bootstrap bootstrap-check env-check env-fingerprint mvp-up stop reset seed demo-reset \
	test test-api test-analyzer test-contracts test-integration mvp-test lint typecheck build smoke generate security

help:
	@printf '%s\n' 'OriginProof MVP commands: bootstrap env-check mvp-up seed smoke mvp-test lint typecheck'

bootstrap:
	@test -f .env || cp .env.example .env
	uv sync --all-packages --all-groups
	pnpm install --lockfile-only

bootstrap-check:
	uv run python scripts/ci/validate_structure.py
	uv run python scripts/ci/env_check.py

env-check:
	uv run python scripts/ci/env_check.py

env-fingerprint:
	uv run python scripts/ci/environment_fingerprint.py

mvp-up:
	docker compose up --build --detach postgres redis anvil api analyzer

stop:
	docker compose stop

reset:
	docker compose down --volumes --remove-orphans

seed:
	uv run python scripts/fixtures/seed.py

demo-reset: reset mvp-up seed

test:
	uv run pytest

test-api:
	uv run --package originproof-api pytest apps/api/tests

test-analyzer:
	uv run --package originproof-analyzer pytest services/analyzer/tests

test-contracts:
	cd packages/contracts && forge test

test-integration:
	uv run pytest apps/api/tests services/analyzer/tests

mvp-test: test-api test-analyzer test-contracts test-integration

lint:
	uv run ruff check apps packages services scripts

typecheck:
	uv run python -m compileall -q apps packages services scripts

build:
	docker compose build api analyzer

smoke:
	sh scripts/ci/smoke.sh

generate:
	uv run python scripts/generate_schemas.py

security:
	@printf '%s\n' 'Run dependency and secret scans in CI after Bootstrap dependencies are locked.'
