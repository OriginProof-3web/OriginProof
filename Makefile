FOUNDRY_BIN_DIR ?= $(HOME)/.foundry/bin
FORGE := $(FOUNDRY_BIN_DIR)/forge
ANVIL := $(FOUNDRY_BIN_DIR)/anvil

.PHONY: bootstrap bootstrap-contracts test test-contracts test-python lint chain deploy-local export-abi

bootstrap: bootstrap-contracts
	uv sync

bootstrap-contracts:
	./packages/contracts/script/bootstrap_dependencies.sh

test: test-python test-contracts

test-contracts:
	cd packages/contracts && $(FORGE) test -vvv

test-python:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .
	cd packages/contracts && $(FORGE) fmt --check

chain:
	$(ANVIL) --chain-id 31337

deploy-local:
	./packages/contracts/script/deploy_local.sh

export-abi:
	./packages/contracts/script/export_abi.sh
