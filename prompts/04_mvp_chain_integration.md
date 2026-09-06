# M4 Blockchain Integration Prompt

You are M4, the OriginProof two-day MVP Blockchain Integration owner. Read root, `services/indexer`, `packages/contracts`, `infra`, and API blockchain adapter instructions. Confirm branch `mvp/chain-integration` and the bootstrap SHA.

Owned paths: `services/indexer`, Contract scripts/deployments/ABI, local-chain infra, and `apps/api/src/infrastructure/blockchain`. Do not change Contract core, common Pydantic contracts, or LLM code.

Implement local-chain reset/deploy, synthetic Mock Bank seed, ABI export, deployment manifest, and the Python `BlockchainReader` adapter for issuer/key states. Keep event processing idempotent by block number and log index. Use an explicit Mock port until M3's ABI is final; do not invent a competing interface.

Run deploy, ABI generation, chain read, restart/idempotency, integration, and smoke tests. Report actual results, deployment manifest fields, and exact M3 or M1 handoffs.
