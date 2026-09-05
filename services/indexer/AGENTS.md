# Blockchain Integration Agent Instructions

## 1. Scope
Applies to `services/indexer` and coordinates with the API blockchain adapter. Read the root `AGENTS.md` first.

## 2. Responsibility
M4 owns local-chain deployment, ABI export, deployment manifests, Python Web3 adapter, event projection and integration tests.

## 3. Allowed Changes
Edit indexer, approved deploy and ABI paths, and `apps/api/src/infrastructure/blockchain` through the M4-owned boundary.

## 4. Prohibited Changes
Do not change Contract core logic or frozen API and Pydantic contracts without handoff. Do not treat a DB projection as chain authority.

## 5. Contracts
Use block number and log index for idempotency. Store chain ID, address, commit SHA and deployment arguments in the manifest. Support local-chain reset.

## 6. Required Tests
Run deploy smoke, ABI generation, issuer and key reads, duplicate event replay and restart checkpoint tests.

## 7. Completion
`make demo-reset` deploys and seeds the Mock Bank. The API can read active and revoked key states through the port.

## 8. Handoff
Contract interface issues go to M3 with the failing call, ABI item, chain state and expected behavior.
