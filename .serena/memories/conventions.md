# Conventions and Invariants

- AI returns `CardPaymentNoticeCandidate` only; it never labels authenticity, queries registry trust, or exposes raw provider output. Unknown fields are null.
- All model access goes through `LLMProvider`; implement OpenAI and Mock adapters. Handle refusal, incomplete output, timeout, rate limit, and schema mismatch.
- Deterministic verifier owns status and reason codes. `NOT_REGISTERED` does not mean fake.
- Canonicalization: UTF-8 NFC, sorted keys, UTC timestamps, integer minor currency units. Shared Pydantic models are authoritative; generated JSON Schema/OpenAPI/TypeScript artifacts come from source generators.
- Never log keys, full images, raw private data, or unrestricted model responses. Never put secrets, personal data, raw documents, or full proof payloads on-chain.
- Use synthetic, clearly mock-labeled fixtures. Validate upload signature, MIME, size, and page count. Use nonce, expiry, domain separation, explicit key revocation.
- Ownership: M1 API/shared Python + final integration; M2 analyzer/fixtures; M3 contract core/tests; M4 indexer/deploy/ABI and API chain adapter. Do not edit another owner's paths without handoff/acknowledgment.
- Keep frozen contracts stable; generated files change only through their generator. Do not create top-level directories outside apps/services/packages/fixtures/infra/scripts/docs/.github.