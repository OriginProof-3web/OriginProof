# Handoff: M1 to M2 — Card payment notice candidate contract

Requesting role: M1 Backend

Target owner: M2 AI

Exact interface: `CardPaymentNoticeCandidate` in
`packages/schemas/generated/json/card-payment-notice-candidate.schema.json`.

M2 returns extracted candidate fields, a numeric confidence from `0` to `1`, a possible `proof_id`,
and `missing_fields`. It must not return a verification status, authenticity score, or any final
decision.

M1 compares only fields actually present in the candidate with the server-side signed proof. The
MVP’s altered-amount fixture must preserve every other field and return `TAMPERED` with
`AMOUNT_MISMATCH` from the backend verifier.
