# MVP 3-minute demo

This demo uses only the synthetic Origin Mock Bank fixture and a local Ganache chain.
It must not be used with real credentials, transactions, or production infrastructure.

## Reset and verify

From the repository root, run:

```bash
make demo-reset
```

The command removes only this project's Docker Compose volumes, starts PostgreSQL, Redis, local
Ganache, API, and Analyzer, applies the migration, seeds the synthetic Signed Proof, deploys and
registers the synthetic issuer/key, reloads the API with the generated manifest, and verifies both
HTTP cases.

Expected final output:

```text
MVP HTTP E2E passed: VERIFIED + ACTIVE; TAMPERED + AMOUNT_MISMATCH
```

## Explain the two results

1. `fixtures/mvp/card_notice_valid.json` matches the server-side signed proof. The API returns
   `VERIFIED + ACTIVE` after payload, issuer, key, and signature checks.
2. `fixtures/mvp/card_notice_amount_tampered.json` changes only the amount. The API returns
   `TAMPERED + AMOUNT_MISMATCH`; the analyzer does not make that authenticity decision.

For an interactive view, open `http://127.0.0.1:8000/docs` after the reset. Do not paste real
personal or payment data into the local Swagger UI.
