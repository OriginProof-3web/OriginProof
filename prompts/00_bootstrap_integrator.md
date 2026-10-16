# Bootstrap Integrator Prompt

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../START_HERE.md)와 [개발 계획서](../docs/development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

You are the OriginProof repository bootstrap integrator.

Before editing, read the root `AGENTS.md`, `CLAUDE.md`, `START_HERE.md`, `repo_structure_manifest.json`, and every deeper `AGENTS.md` relevant to files you will change. First report:

1. Loaded instruction files.
2. Current branch and commit SHA.
3. Planned files and directories.
4. Commands you will use to verify the result.
5. Any blocking ambiguity.

Goal:

1. Create the documented monorepo skeleton without new top-level directories.
2. Create a reproducible Docker Compose development environment for FastAPI, Analyzer, PostgreSQL, Redis, and a local EVM.
3. Pin runtime versions and commit Python, Node, and Contract lock or revision files.
4. Implement stable Make targets: `bootstrap`, `bootstrap-check`, `env-check`, `env-fingerprint`, `mvp-up`, `stop`, `seed`, `smoke`, `test-api`, `test-analyzer`, `test-contracts`, `test-integration`, and `mvp-test`.
5. Create `.env.example` with safe development values and no secrets.
6. Create the initial `CARD_PAYMENT_NOTICE`, `CardPaymentNoticeCandidate`, `SignedProofEnvelope`, status, lifecycle, and reason-code contracts.
7. Add synthetic normal and amount-tampered fixtures.
8. Make `python scripts/ci/validate_structure.py`, `make env-check`, and `make smoke` pass from a clean clone.

Constraints:

1. Do not use real organizations, people, cards, transactions, documents, or secrets.
2. Do not call a paid API or deploy to a public testnet.
3. Do not weaken or disable a failing check.
4. AI extracts candidate fields only and never returns authenticity.
5. Keep shared contracts minimal and document any assumption.

Continue through implementation, testing, diff review, and documentation until the completion conditions are met. Stop only for a real permission, secret, external cost, destructive action, or material product decision blocker.

At the end report implemented changes, files changed, commands actually run and their results, shared-contract impact, security/privacy impact, handoffs, remaining blockers, and the bootstrap commit to share.
