SHELL := /bin/sh
COMPOSE := COMPOSE_PROJECT_NAME=originproof docker compose
UV_ENV := .uv-venv
UV := UV_PROJECT_ENVIRONMENT=$(UV_ENV) uv
WORKSPACE_PYTHONPATH := apps/api/src:packages/python:services/analyzer/src

.DEFAULT_GOAL := help



.PHONY: help bootstrap bootstrap-check env-check env-fingerprint mvp-up stop reset db-upgrade seed deploy-local api-reload mvp-e2e db-smoke demo demo-reset demo-stop \
	test test-api test-analyzer test-contracts test-integration mvp-test lint typecheck build smoke generate security

help:
	@printf '%s\n' 'OriginProof commands (MVP regression retained): demo demo-stop bootstrap env-check mvp-up seed smoke mvp-test lint typecheck'

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
	$(COMPOSE) up --build --detach postgres redis anvil api analyzer web

stop:
	$(COMPOSE) stop

reset:
	$(COMPOSE) down --volumes --remove-orphans

db-upgrade:
	$(COMPOSE) exec -T api uv run --package originproof-api alembic -c apps/api/alembic.ini upgrade head

seed: db-upgrade
	SEED_DATABASE_URL=postgresql+asyncpg://originproof:originproof@127.0.0.1:5432/originproof PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-api python scripts/fixtures/seed.py

deploy-local: seed
	@OP_SIGNER=$$($(UV) run --package originproof-api python -c "import json; print(json.load(open('build/seed_manifest.json'))['signer'])"); \
	OP_SHA=$$(git rev-parse HEAD); \
	$(COMPOSE) run --rm --build deployer uv run --package originproof-api python packages/contracts/script/deploy_local.py --rpc-url http://anvil:8545 --signer "$$OP_SIGNER" --source-commit-sha "$$OP_SHA"

api-reload:
	$(COMPOSE) up --detach --force-recreate api

mvp-e2e: mvp-up deploy-local api-reload
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-api python scripts/ci/mvp_http_e2e.py
	$(MAKE) smoke

db-smoke: seed
	SEED_DATABASE_URL=postgresql+asyncpg://originproof:originproof@127.0.0.1:5432/originproof PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-api python scripts/ci/proof_storage_smoke.py

demo-reset: reset mvp-e2e

# One-command demo: starts, seeds, deploys, and verifies all services without deleting local data.
demo: mvp-e2e
	@curl --fail --silent --show-error --retry 15 --retry-all-errors --max-time 3 http://127.0.0.1:3000/ >/dev/null
	@printf '\nDemo ready — open: http://127.0.0.1:3000\n'

demo-stop: stop

test:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run pytest

test-api:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --all-packages --all-groups pytest apps/api/tests

test-analyzer:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --all-packages --all-groups pytest services/analyzer/tests

test-contracts:
	$(COMPOSE) run --rm --no-deps --build deployer sh -lc 'cd packages/contracts && forge test'

test-integration:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run pytest apps/api/tests services/analyzer/tests

mvp-test: test-api test-analyzer test-contracts test-integration

lint:
	$(UV) run ruff check apps packages/python services scripts
	pnpm --filter originproof-demo-web lint

typecheck:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run python -m compileall -q apps packages services scripts
	pnpm --filter originproof-demo-web typecheck

build:
	$(COMPOSE) build api analyzer web

smoke:
	sh scripts/ci/smoke.sh

generate:
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-core python scripts/generate_schemas.py
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-core python scripts/generate_golden_fixture.py
	PYTHONPATH=$(WORKSPACE_PYTHONPATH) $(UV) run --package originproof-core python scripts/generate_wallet_contracts.py

security:
	@printf '%s\n' 'Run dependency and secret scans in CI after Bootstrap dependencies are locked.'
