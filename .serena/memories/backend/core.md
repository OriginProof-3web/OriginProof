# Backend and Shared Python Core

- `apps/api`: FastAPI, request orchestration, persistence/migrations, proof resolver, deterministic verification, public errors/endpoints. Use Pydantic contracts, typed public responses, request/task-scoped AsyncSession.
- `packages/python/originproof_core`: authoritative Pydantic domain models, canonicalization, signatures, reason codes and deterministic rules; no HTTP, DB, UI, provider or filesystem dependencies.
- Dependency direction: API → core package; core never imports apps/services.
- Shared contract changes require M1 ownership, Schema/version and golden-fixture updates; generated artifacts are not hand-edited.
- Verification outputs keep verification status and lifecycle status separate and include stable reason codes/checks/request ID. AI output is candidate input only.