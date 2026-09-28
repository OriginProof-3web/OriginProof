# OriginProof

- Mission: verify issuer, protected-field integrity, and proof lifecycle; this is deterministic evidence verification, not phishing classification.
- MVP flow: synthetic notice → analyzer candidate fields → Pydantic validation → Signed Proof lookup → signature/canonical payload comparison → issuer/key registry check → VERIFIED or TAMPERED.
- AI only extracts fields; only backend deterministic checks produce authenticity status. Use synthetic Mock Bank data; no real customer/bank data.
- Authority boundaries: `packages/python/originproof_core` owns shared Python contracts and deterministic verification; `apps/api` orchestrates; `services/analyzer` extracts candidates; `packages/contracts` owns registry trust state; `services/indexer` projects chain events and reads chain state; `apps/web` is post-MVP UI.
- Dependencies flow apps/services → packages; packages do not depend on apps/services. Verification core has no HTTP/DB/UI/provider dependency.
- Frozen MVP contracts require M1 ownership and handoff for other owners. Root `AGENTS.md` is authoritative; nested AGENTS.md files define path ownership.
- Read focused module notes: backend contracts/orchestration in `mem:backend/core`; extraction in `mem:analyzer/core`; registry and indexer boundaries in `mem:blockchain/core`; post-MVP UI in `mem:web/core`.
- Stack and versions: `mem:tech_stack`; durable coding rules: `mem:conventions`; commands: `mem:suggested_commands`; completion checks: `mem:task_completion`.