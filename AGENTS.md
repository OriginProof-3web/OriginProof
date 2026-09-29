# OriginProof Agent Instructions

## 1. Scope

This file applies to the entire repository. Read it before inspecting, creating, or editing files. A deeper `AGENTS.md` adds path-specific rules but cannot weaken the security, privacy, schema, or collaboration rules defined here.

## 2. Mission

OriginProof verifies whether an important digital request or evidence item was issued by the claimed issuer, whether protected fields changed, and whether the proof remains valid.

Do not build a phishing classifier. AI extracts candidate fields only. `VERIFIED` is produced only by deterministic checks against a Signed Proof and trusted issuer or key state.

## 3. Current MVP

The two-day MVP uses one synthetic `Origin Mock Bank` card payment notification.

Required flow:

```text
Synthetic card notice image or text
-> GPT-5.6 Luna field extraction
-> Pydantic validation
-> Signed Proof lookup
-> signature and canonical payload comparison
-> Issuer and Key Registry check
-> VERIFIED or TAMPERED report
```

Required results:

1. Normal notice: `VERIFIED` and `ACTIVE`.
2. Changed amount: `TAMPERED` and `AMOUNT_MISMATCH`.
3. AI never returns authenticity status.
4. No real bank, customer, card, or transaction data is used.
5. The original two-day MVP gate used Swagger, CLI, and JSON reports; this restriction does not apply to post-MVP web development.

## 3A. Finals Development Scope

The initial MVP gate is complete. Read `docs/development_plan.md` for finals work: seven development
weeks followed by two presentation days. The required product includes user verification, an issuer
console, and operator views for issuer approval, public key management, and Proof issuance/revocation.
The plan describes target behavior, not completed implementation. Preserve approved model, Schema,
signing, and ABI contracts until their owners review a change. The plan is the canonical planning
document; do not maintain a competing copy outside the repository.

## 4. Fixed Stack

1. Python, uv workspace
2. FastAPI, Pydantic
3. SQLAlchemy 2, Alembic, PostgreSQL
4. Redis, Celery
5. OpenAI Responses API through `LLMProvider`
6. Default model from `OPENAI_MODEL`, default value `gpt-5.6-luna`
7. Solidity, Foundry, OpenZeppelin, local EVM and one testnet
8. Next.js and TypeScript only after the two-day MVP
9. Docker Compose, Makefile, GitHub Actions

Do not replace a fixed technology or add an equivalent framework without an accepted ADR.

## 5. Read Order

Before editing:

1. Current issue and acceptance criteria
2. This root file, `START_HERE.md`, and the relevant scope, weekly deliverables, and acceptance criteria in `docs/development_plan.md`
3. Every deeper `AGENTS.md` between root and the target file
4. Relevant Schema, OpenAPI, ABI, ADR, test and fixture
5. `git status` and existing user changes

Claude Code must also read `CLAUDE.md`, which points back to the authoritative `AGENTS.md` files.

At the start of every task, report loaded instruction files, current branch and SHA, owned and prohibited paths, planned files, and verification commands before editing.

## 5A. Environment Contract

Feature work starts only after all four members use the same bootstrap SHA and pass structure validation, environment checks, smoke tests, and environment fingerprint comparison. Lockfiles and runtime version files are authoritative. Unit and integration tests must use Mock providers by default and must not depend on an individual's paid API key.

A PR is not complete until its author runs owned-area tests and the assigned reviewer reproduces the change from a clean worktree or clone.

## 6. Repository Contract

Do not create new top-level directories. Use only:

```text
apps/ services/ packages/ fixtures/ infra/ scripts/ docs/ .github/
```

Dependency direction:

```text
apps and services -> packages
packages -> no apps or services
verification core -> no HTTP, DB, UI or provider dependency
analyzer -> candidate fields only
API -> orchestration and deterministic verification
contracts -> shared trust state only
```

Do not create alternative folders such as `src2`, `new`, `temp`, `final`, or duplicate schema modules. Generated files must be changed through their source generator.

## 7. Shared Contracts

The authoritative Python domain models live in `packages/python/originproof_core`. Generate JSON Schema, OpenAPI and TypeScript types from approved source models.

The two-day MVP freezes:

1. `CARD_PAYMENT_NOTICE`
2. `CardPaymentNoticeCandidate`
3. `SignedProofEnvelope`
4. Verification and Lifecycle enums
5. Reason Codes
6. Contract events and ABI

M1 owns changes to frozen shared contracts during the MVP. Other owners must write a handoff request, and final integration requires M1's review and merge. Kim Hyeongjun supports review and integration coordination.

## 8. LLM Rules

1. Access models only through `LLMProvider`.
2. Implement `OpenAILLMProvider` and `MockLLMProvider`.
3. Read provider, model, reasoning effort, timeout and retries from settings.
4. Use OpenAI Responses API and Pydantic Structured Outputs.
5. The prompt extracts only fields present in the input and uses null for unknown values.
6. Do not ask the model whether the notice is genuine, fraudulent, safe, or malicious.
7. Handle refusal, incomplete output, timeout, rate limit and schema mismatch explicitly.
8. Never log API keys, full input images, raw private data, or unrestricted model responses.
9. Unit tests use `MockLLMProvider`; live API tests are opt-in.

## 9. Security and Privacy

1. Never put private keys, API tokens, personal data, raw documents or full payloads on-chain.
2. Never commit real bank branding or real card transaction data.
3. Use synthetic values and clearly mark the issuer as mock.
4. Validate file signature, MIME, size and page count before processing.
5. Mask sensitive values in logs and reports.
6. Use nonce, expiry, domain separation and explicit key revocation.
7. `NOT_REGISTERED` does not mean fake.
8. Never claim legal validity or guaranteed fraud prevention.

## 10. Four-person Ownership During MVP

1. M1 Backend: `apps/api`, `packages/python/originproof_core`
2. M2 AI: `services/analyzer`, `fixtures/mvp`
3. M3 Blockchain Core: `packages/contracts/src`, `packages/contracts/test`
4. M4 Blockchain Integration: `services/indexer`, deployment and ABI outputs, `apps/api/src/infrastructure/blockchain`

M1 owns Backend, shared Python contracts, and final integration and merge decisions. Kim Hyeongjun (`@kimhyounjun`) supports review and integration coordination. M3 owns Contract interfaces. M4 owns deployment manifests and Python chain adapters. Do not edit another owner's path without a written handoff and acknowledgement.

## 11. Git and Merge Safety

All four branches start from the same bootstrap commit SHA.

```text
mvp/backend
mvp/ai
mvp/chain-core
mvp/chain-integration
mvp/integration
```

Only M1 merges into `mvp/integration` and `main`; Kim Hyeongjun (`@kimhyounjun`) supports review and integration coordination. Do not force push shared branches, reset user changes, rewrite unrelated files, or mix formatting-only changes with feature work. A newly created integration branch with no dependent PRs may be corrected to the verified `main` SHA only with M1's explicit authorization and a team notice.

### GitHub CLI and Network Access

1. Use `gh` for GitHub pull request, issue, branch, and workflow operations. Use the browser only when the CLI and available GitHub connectors cannot complete the task or the task requires the UI.
2. A network error from a sandboxed shell does not establish that GitHub CLI authentication is invalid. Retry the same `gh` command with network access enabled before diagnosing the login or switching to the browser.
3. Each teammate authenticates on their own machine and checks `gh auth status` with network access available. Never copy or commit tokens, and never ask teammates to share credentials.

## 12. Required Commands

The stable root interface is:

```text
make bootstrap-check
make mvp-up
make demo-reset
make mvp-test
make lint
make typecheck
make test
make smoke
```

If a required command does not exist, M1 creates the minimal implementation before parallel work begins. Do not invent a competing command name.

## 13. Agent Work Loop

```text
Read instructions -> inspect existing patterns -> state affected paths
-> implement the smallest coherent change -> add tests
-> run narrow checks -> run required broad checks -> review diff
-> update docs or generated artifacts -> report results and risks
```

Before creating files, state which `AGENTS.md` files apply. Ask before destructive actions, breaking contracts, new dependencies, top-level paths, real external writes, production deployment, or paid API calls outside an explicitly authorized live test.

## 14. Definition of Done

1. Acceptance criteria are met.
2. Tests for normal and failure paths pass.
3. Format, lint, typecheck and build pass for the changed scope.
4. Schema, OpenAPI, ABI and migration outputs are current.
5. Security and privacy impact is checked.
6. Another team member can reproduce the result.
7. The final report lists changed files, executed commands, actual results and remaining risks.

## 15. Handoff Format

When another owner must change something, create a short handoff with:

1. Requested change
2. Exact file or interface
3. Reason and blocking issue
4. Input and expected output example
5. Required tests
6. Deadline and requesting branch or commit
