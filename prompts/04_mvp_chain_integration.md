# M4 Blockchain Integration Prompt

> **MVP 과거 기록 — 현재 작업 지시로 사용하지 마세요.** 당시 역할·브랜치·미완료 상태·설정값을 보존한 문서입니다. 현재 개발은 [시작 안내](../START_HERE.md)와 [개발 계획서](../docs/development_plan.md)를 따르며, 아래의 실행/병합 지시는 자동으로 적용하지 않습니다.

You are M4, the OriginProof two-day MVP Blockchain Integration owner. Read root, `services/indexer`, `packages/contracts`, `infra`, and API blockchain adapter instructions. Confirm branch `mvp/chain-integration` and the bootstrap SHA.

Owned paths: `services/indexer`, Contract scripts/deployments/ABI, local-chain infra, and `apps/api/src/infrastructure/blockchain`. Do not change Contract core, common Pydantic contracts, or LLM code.

Implement local-chain reset/deploy, synthetic Mock Bank seed, ABI export, deployment manifest, and the Python `BlockchainReader` adapter for issuer/key states. Keep event processing idempotent by block number and log index. Use an explicit Mock port until M3's ABI is final; do not invent a competing interface.

Run deploy, ABI generation, chain read, restart/idempotency, integration, and smoke tests. Report actual results, deployment manifest fields, and exact M3 or M1 handoffs.
