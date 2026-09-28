# OriginProof Start Here

## Finals development

Read the [development plan](docs/development_plan.md) before planning or implementing finals work.
It is the repository's canonical plan for seven development weeks followed by two presentation days.
Check its roles and permissions (section 3), weekly deliverables (15), acceptance criteria (16),
and mandatory scope (17), then read the current models, API, ABI, and path-specific instructions.
The plan defines future work; it does not replace approved runtime contracts or mark features complete.

The initial MVP gate is complete. The startup sequence below is retained as the original bootstrap
record. Use the current agreed integration base for new work rather than restarting from the old
bootstrap commit. Finals work includes the user verification app, issuer console, and operator views.

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

## Branches

```text
mvp/backend
mvp/ai
mvp/chain-core
mvp/chain-integration
mvp/integration
```

## Shared completion rule

A change is complete only after the author tests it and the assigned reviewer reproduces it in a clean worktree or clone.
