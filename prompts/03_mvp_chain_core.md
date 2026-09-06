# M3 Blockchain Core Prompt

You are M3, the OriginProof two-day MVP Blockchain Core owner. Read root and `packages/contracts` instructions, then confirm branch `mvp/chain-core`, bootstrap SHA, planned files, and tests.

Owned paths: `packages/contracts/src` and `packages/contracts/test`. Do not edit deploy/ABI ownership, API, Analyzer, or shared Pydantic contracts.

Implement the minimum Issuer and Issuer Key registries with separated roles, active/suspended/revoked states, irreversible key revocation, indexed events, zero-address and duplicate guards. Store no raw Proof or personal data on-chain. Add Foundry unit, fuzz, authorization, state-transition, and event tests.

Run structure, Contract, lint/static security, and relevant integration checks. Give M4 an exact ABI/interface handoff and report every actual command and result.
