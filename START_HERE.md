# OriginProof Start Here

## Finals development

Read the [development plan](docs/development_plan.md) before planning or implementing finals work.
It is the repository's canonical plan for seven development stages, not fixed calendar weeks.
Prepared test accounts, a local web demo, and local EVM are the required scope; other deployment
and authentication options require a later team decision.
Check its roles and permissions (section 3), stage deliverables and agent workflow (15), acceptance criteria (16),
and mandatory scope (17), then read the current models, API, ABI, and path-specific instructions.
The plan defines future work; it does not replace approved runtime contracts or mark features complete.

The initial MVP gate is complete. The startup sequence below is retained as the original bootstrap
record. Use the current agreed integration base for new work rather than restarting from the old
bootstrap commit. Finals work includes the user verification app, issuer console, and operator views.

## Finals branch flow

PR #19 is merged. The long-lived `integration` branch starts from the resulting `main`. For implementation, create task branches from the active `phase/W1`–`phase/W7` branch and target PRs to that phase. Once all stage acceptance criteria, reviews, and checks pass, the coordinator promotes the phase to `integration` through a PR and preserves the phase branch at its final SHA for the portfolio. Multi-stage bundles use separate phase PRs; follow development plan sections 14 and 15.1 for dependencies, early independent work, synchronization, and evidence. Planning and workflow documentation may target `integration` directly through a PR. These are agent execution rules, not an installed background automation.

Run integration verification and open an `integration` → `main` PR only when Jordi2801K explicitly requests it; coordinate each promotion through one assigned person or agent. The current private-repository plan does not support GitHub branch protection, so follow the PR, review, and no-direct-push rules as team policy. Preserve `mvp/integration` as an MVP-era snapshot and use the `mvp-final` tag for the verified MVP completion commit.

## Original MVP bootstrap

This repository must be bootstrapped once before four people work in parallel.

## Team startup order

1. One integrator applies this scaffold at the Git root.
2. The integrator gives an agent `prompts/00_bootstrap_integrator.md`.
3. Merge the bootstrap PR and share its exact commit SHA.
4. Every member checks out that SHA and runs:

```bash
cp .env.example .env
make bootstrap
make env-check
make mvp-up
make seed
make smoke
make env-fingerprint
```

5. Compare the `comparable` section of `build/environment_fingerprint.json` across all four machines. The informational host platform may differ when the same containers are used.
6. Create only the assigned branch from the shared SHA.
7. Give the assigned prompt in `prompts/` to Codex or Claude Code.

Do not start feature work when the SHA, lockfile hashes, Schema hash, ABI hash, or smoke result differs.

## Historical MVP branches

```text
mvp/backend
mvp/ai
mvp/chain-core
mvp/chain-integration
mvp/integration
```

## Shared completion rule

A change is complete only after the author tests it and the assigned reviewer reproduces it in a clean worktree or clone.
