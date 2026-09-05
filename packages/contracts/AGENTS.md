# Contract Agent Instructions

## 1. Scope
Applies to `packages/contracts`. Read the root `AGENTS.md` first.

## 2. Responsibility
M3 owns Issuer and Key Registry contract interfaces, access control, state transitions, events and Foundry tests.

## 3. Allowed Changes
M3 edits `src` and `test`. M4 edits deployment scripts, ABI exports and manifests. Coordinate before touching a shared interface.

## 4. Prohibited Changes
Do not store raw notification text, card data, personal data or full Proof payloads on-chain. Do not add tokens, payments, upgradeability or governance to the MVP.

## 5. Contracts
Emit indexed events for issuer and key changes. Reject zero addresses, duplicates and unauthorized transitions. Key revocation is irreversible.

## 6. Required Tests
Run Foundry unit, authorization, boundary and fuzz tests. Include active, suspended and revoked key states.

## 7. Completion
ABI and event behavior are stable, tests pass and deployment consumers can read issuer and key state.

## 8. Handoff
Interface changes require an ABI diff, reason, migration impact and M4 acknowledgement before merge.
