# API Agent Instructions

## 1. Scope
Applies to `apps/api`. Read the root `AGENTS.md` first.

## 2. Responsibility
M1 owns the FastAPI application, SQLAlchemy repositories, Alembic migrations, proof resolver, deterministic verification orchestration, API errors and MVP CLI-facing endpoints.

## 3. Allowed Changes
Edit `apps/api` and approved shared Python models. During MVP, only M4 may edit `src/infrastructure/blockchain` unless a handoff is accepted.

## 4. Prohibited Changes
Do not implement LLM prompts, Solidity internals or frontend code. Do not return `VERIFIED` from an AI result. Do not use untyped response dictionaries as public contracts.

## 5. Contracts
Use Pydantic models from `packages/python/originproof_core`. Provider access must use ports. Use a new SQLAlchemy `AsyncSession` per request or task.

## 6. Required Tests
Run API unit tests, async httpx tests, migration smoke tests, normal and amount-mismatch integration tests, lint and typecheck.

## 7. Completion
The endpoint returns stable status, lifecycle, reason codes, checks and request ID. OpenAPI is current and no secret or raw notification is logged.

## 8. Handoff
For Schema, Contract or LLM changes, provide exact input, expected output, blocking test and target owner.
