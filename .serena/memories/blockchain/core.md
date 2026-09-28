# Blockchain and Indexer

- `packages/contracts` (M3) owns Issuer/Key Registry interfaces, state transitions, events and Solidity tests; `services/indexer` (M4) owns deployment, ABI/manifests, Python Web3 adapter, and event projections. M4 also owns `apps/api/src/infrastructure/blockchain`.
- Chain is authoritative for issuer/key trust state; DB projection is not chain authority. API verifier consumes trust state through a port.
- Store only shared trust state on-chain. Never store raw notice, personal/card data, or full proof payloads.
- Events use block number + log index for idempotency. Manifests include chain ID, address, source commit SHA, and deployment arguments. Support local-chain reset.
- Reject zero addresses, duplicates, unauthorized transitions; key revocation is irreversible. Contract interface changes require ABI diff and M4 acknowledgment.