SHELL := /bin/sh
COMPOSE := COMPOSE_PROJECT_NAME=originproof docker compose
UV_ENV := .uv-venv
UV := UV_PROJECT_ENVIRONMENT=$(UV_ENV) uv
WORKSPACE_PYTHONPATH := apps/api/src:packages/python:services/analyzer/src

.DEFAULT_GOAL := help


.PHONY: help bootstrap bootstrap-check env-check env-fingerprint mvp-up stop reset db-upgrade seed db-smoke demo-reset \
	test test-api test-analyzer test-contracts test-integration mvp-test lint typecheck build smoke generate security

help:
	@printf '%s\n' 'OriginProof MVP commands: bootstrap env-check mvp-up seed smoke mvp-test lint typecheck'

bootstrap:
	@test -f .env || cp .env.example .env
	$(UV) sync --all-packages --all-groups
	pnpm install --lockfile-only

bootstrap-check:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python scripts/ci/validate_structure.py
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python scripts/ci/env_check.py

env-check:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python scripts/ci/env_check.py

env-fingerprint:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python scripts/ci/environment_fingerprint.py

mvp-up:
	$(COMPOSE) up --build --detach postgres redis anvil api analyzer

stop:
	$(COMPOSE) stop

reset:
	$(COMPOSE) down --volumes --remove-orphans

db-upgrade:
	$(COMPOSE) exec -T api uv run --package originproof-api alembic -c apps/api/alembic.ini upgrade head

seed: db-upgrade
	SEED_DATABASE_URL=postgresql+asyncpg://originproof:originproof@127.0.0.1:5432/originproof PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-api python scripts/fixtures/seed.py

db-smoke: seed
	SEED_DATABASE_URL=postgresql+asyncpg://originproof:originproof@127.0.0.1:5432/originproof PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-api python scripts/ci/proof_storage_smoke.py

demo-reset: reset mvp-up seed

test:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run pytest

test-api:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-api pytest apps/api/tests

test-analyzer:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-analyzer pytest services/analyzer/tests

test-contracts:
	cd packages/contracts && forge test

test-integration:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run pytest apps/api/tests services/analyzer/tests

mvp-test: test-api test-analyzer test-contracts test-integration

lint:
	$(UV) run ruff check apps packages/python services scripts

typecheck:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python -m compileall -q apps packages services scripts

build:
	$(COMPOSE) build api analyzer

smoke:
	sh scripts/ci/smoke.sh

generate:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python scripts/generate_schemas.py
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python scripts/generate_golden_fixture.py

security:
	@printf '%s\n' 'Run dependency and secret scans in CI after Bootstrap dependencies are locked.'
