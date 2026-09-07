# MVP card-notice verification API

The local OpenAPI contract is available at `http://127.0.0.1:8000/openapi.json` after `make mvp-up`.
Swagger UI is available at `http://127.0.0.1:8000/docs`.

## `POST /v1/mvp/card-notices/verify`

The endpoint accepts an untrusted extracted candidate and a server-side `proof_id`. It does not
persist the request body or use the candidate as authenticity evidence.

```json
{
  "proof_id": "prf_demo_001",
  "candidate": {
    "issuer_name": "Origin Mock Bank",
    "masked_card": "1234",
    "amount_minor": 154000,
    "currency": "KRW",
    "merchant": "ORIGIN CAFE",
    "approved_at": "2026-09-03T03:14:00Z",
    "transaction_id": "txn_demo_001",
    "confidence": 1
  },
  "request_id": "req_demo_001"
}
```

Successful responses are typed `VerificationResult` objects and include `verification_status`,
`lifecycle_status`, `reason_codes`, `checks`, `verified_at`, and `request_id`. The API echoes the
valid request ID in `X-Request-ID`.

At `mvp/integration@a1a671b`, PostgreSQL lookup and M4's runtime `BlockchainReader` are both live.
`make demo-reset` starts the fixed local Anvil chain, creates the deployment manifest, reloads the API,
and verifies the final MVP paths through the public HTTP endpoint: the exact candidate is `VERIFIED`
with `ACTIVE`, while an altered amount is `TAMPERED` with `AMOUNT_MISMATCH`.

If the manifest, RPC, or chain response is unavailable, the endpoint remains fail-closed and returns
`INCONCLUSIVE` with `DEPENDENCY_UNAVAILABLE`; it does not convert an infrastructure failure into a
successful verification.

Malformed requests return only the safe form below; validation details and submitted values are not
echoed.

```json
{
  "error": "MALFORMED_INPUT",
  "request_id": "req_demo_001"
}
```

## Storage and privacy

`signed_proofs` stores the trusted Signed Proof envelope by `proof_id`. Its seed upsert is
idempotent. Candidate extraction input, raw message/image data, and actual personal or payment data
are not stored, logged, included in fixtures, or written to the chain.
