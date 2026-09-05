# Infrastructure Agent Instructions

## 1. Scope
Applies to `infra` and root runtime configuration. Read the root `AGENTS.md` first.

## 2. Responsibility
This path owns Docker Compose services, local EVM configuration, health checks and reproducible local execution.

## 3. Allowed Changes
M1 coordinates API, DB and Redis configuration. M4 coordinates local chain and deployment configuration.

## 4. Prohibited Changes
Do not commit secrets, production credentials, broad public ports or destructive volume commands. Do not rename stable Make targets.

## 5. Contracts
Use `.env.example`, named health checks and pinned images. `make mvp-up` and `make demo-reset` are stable interfaces.

## 6. Required Tests
Run clean startup, health, reset, seed, restart and volume-isolation smoke tests.

## 7. Completion
A clean machine can start the MVP from documented commands and returns the same deployment manifest and seeded scenario.

## 8. Handoff
Configuration changes include affected service, environment variable, default, migration and rollback instruction.
