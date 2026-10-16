# Bootstrap runbook

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../../START_HERE.md)와 [개발 계획서](../development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

The Bootstrap PR is created from `bootstrap/mvp-v1`. It must not be committed directly to
`main`.

## Team startup

1. Merge the reviewed Bootstrap PR.
2. Share the exact merge commit SHA.
3. Each member checks out that SHA, copies `.env.example` to `.env`, and runs `make bootstrap`.
4. Each member runs `make env-check`, `make mvp-up`, `make seed`, `make db-smoke`, `make smoke`,
   and `make env-fingerprint`.
5. Compare the `comparable` object in `build/environment_fingerprint.json` before creating an
   MVP feature branch.

## Local reset

`make demo-reset` removes only the named Docker Compose volumes for this project and recreates
the synthetic seed state. It must never be used against production infrastructure.

## PostgreSQL Proof storage

`make seed` first applies the Alembic migration, then writes one idempotent synthetic Signed Proof
to PostgreSQL. Repeating the command updates the same `proof_id`; it does not create user data or
persist analyzer input. `make db-smoke` additionally checks that the persisted Proof produces
`VERIFIED` for the exact synthetic candidate and `TAMPERED` for an amount mismatch with a test-only
chain adapter.

The local synthetic signing key is generated under ignored `build/` with file mode 0600. It must
never be copied to a deployment environment, committed, or treated as an issuer key.
