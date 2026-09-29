# W2-C1 operation foundation draft

This branch stacks on the local W1 C implementation. Rebase it on the completed W1 phase before a W2 PR. B/C must agree on Adapter submission, receipt, and restart recovery states before W2-C1 can be marked complete.

- `reserve_operation` commits `PENDING_SUBMISSION` before a future external write. The uniqueness key is `(account_id, action, request_id)`; the request body hash and institution must match on retries. A conflict returns `409 REQUEST_ID_CONFLICT`.
- A repeated request returns the existing operation, including an uncertain one. A caller must inspect chain state before any retransmission; this helper never submits or reports success.
- `GET /v1/operations/{operation_id}` is available to the initiating account or an operator. `GET /v1/audit-events` shows all events to operators and only the caller's institution to issuer accounts. Neither endpoint exposes password hashes, session tokens, or private keys.
- W2-C2/C3 must add the actual state transitions, tx hash, receipt/requery evidence, and restart recovery after B's Adapter contract and implementation are reviewed.
