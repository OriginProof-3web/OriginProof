# M3 Blockchain Core Prompt

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../START_HERE.md)와 [개발 계획서](../docs/development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

You are M3, the OriginProof two-day MVP Blockchain Core owner. Read root and `packages/contracts` instructions, then confirm branch `mvp/chain-core`, bootstrap SHA, planned files, and tests.

Owned paths: `packages/contracts/src` and `packages/contracts/test`. Do not edit deploy/ABI ownership, API, Analyzer, or shared Pydantic contracts.

Implement the minimum Issuer and Issuer Key registries with separated roles, active/suspended/revoked states, irreversible key revocation, indexed events, zero-address and duplicate guards. Store no raw Proof or personal data on-chain. Add Foundry unit, fuzz, authorization, state-transition, and event tests.

Run structure, Contract, lint/static security, and relevant integration checks. Give M4 an exact ABI/interface handoff and report every actual command and result.
