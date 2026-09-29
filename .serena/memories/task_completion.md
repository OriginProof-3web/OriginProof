# Task Completion Checks

- Required root interface: `make mvp-test`, `make lint`, `make typecheck`, `make smoke`; choose checks for the owned area, then run broader checks when needed.
- API/shared Python changes: API and core tests, migration smoke, normal and amount-mismatch flows; lint/typecheck; ensure OpenAPI current.
- Analyzer changes: Mock provider tests, normal/changed notice, refusal, timeout, incomplete and schema-mismatch paths; live API checks are opt-in.
- Contract/indexer changes: Foundry authorization/boundary/state tests; deploy smoke and ABI generation; event replay/idempotency and restart checkpoint for indexer.
- Web changes: TypeScript typecheck, component/accessibility checks, and Playwright E2E for supported flows.
- Generated schema/ABI changes: regenerate from approved source and verify clean regeneration; update fixtures and compatibility artifacts.
- Do not report tests as passed unless they were run; PR author runs owned-area tests and reviewer reproduces from a clean worktree/clone.