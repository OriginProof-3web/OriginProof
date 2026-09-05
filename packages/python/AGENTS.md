# Shared Python Core Agent Instructions

## 1. Scope
Applies to `packages/python`. Read the root `AGENTS.md` first.

## 2. Responsibility
This path owns Pydantic domain models, canonicalization, signature verification, deterministic rules, reason codes and generated Schema sources.

## 3. Allowed Changes
During MVP, M1 is the only merger for this path. M2, M3 and M4 submit handoff requests with failing fixtures.

## 4. Prohibited Changes
No FastAPI routers, SQLAlchemy models, OpenAI SDK objects, Web3 clients or filesystem access. Keep the core deterministic and provider independent.

## 5. Contracts
Canonicalization uses UTF-8 NFC, sorted keys, UTC timestamps and integer minor currency units. Schema changes require version and Golden Fixture updates.

## 6. Required Tests
Run Pydantic validation, canonical hash Golden Fixtures, signature checks and every verification state or reason-code unit test.

## 7. Completion
The same input always yields the same canonical bytes, hash and rule result without network access.

## 8. Handoff
Provide old and new Schema, expected hash, compatibility impact and required generated artifacts.
