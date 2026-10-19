# W1 C API contract draft

This is a C-side implementation draft for A and B to review before W1 is marked complete.
It does not change the existing card-notice verification endpoint or activate an issuer on chain.

## Prepared accounts and sessions

- Roles: `operator`, `issuer`, `recipient`. Each issuer account has one fixed `issuer_id` assigned by the local seed command. The client cannot choose its role or institution.
- `POST /v1/auth/login` accepts `{username, password}` and returns `{account_id, username, role, issuer_id, csrf_token}`. It sets an eight-hour host-only, HttpOnly, SameSite=Lax session cookie. Set `API_SESSION_COOKIE_SECURE=true` for HTTPS. Login failures return `401 INVALID_CREDENTIALS`.
- `GET /v1/auth/me` returns the same account fields and current CSRF token. A missing or expired session returns `401 AUTH_REQUIRED`.
- `POST /v1/auth/logout` requires `X-CSRF-Token`, deletes the server session, and clears the cookie. Other authenticated writes also require that header; failure returns `403 CSRF_REQUIRED`.
- The Next.js `/api/:path*` rewrite keeps the browser request on its own origin. A should confirm the fields and error states before connecting the login UI. The current implementation has no public signup or external login.

Run the migration before creating accounts. Create the prepared accounts locally with the CLI below; it prompts for each password without placing it in a command argument, response, or repository file. Use synthetic usernames and distinct passwords. Set `API_DATABASE_URL` to a reachable local database when running outside Compose.

```sh
PYTHONPATH=apps/api/src:packages/python python scripts/fixtures/seed_accounts.py demo-operator operator
PYTHONPATH=apps/api/src:packages/python python scripts/fixtures/seed_accounts.py demo-issuer-a issuer --issuer-id iss_demo_a
PYTHONPATH=apps/api/src:packages/python python scripts/fixtures/seed_accounts.py demo-issuer-b issuer --issuer-id iss_demo_b
PYTHONPATH=apps/api/src:packages/python python scripts/fixtures/seed_accounts.py demo-recipient recipient
```

## Institution application

- `POST /v1/issuer-applications` accepts `{issuer_name}` from an issuer account. The `issuer_id` comes from the authenticated account. One application per institution is allowed in this draft.
- `GET /v1/issuer-applications/mine` returns only the caller's institution application.
- `GET /v1/operator/issuer-applications` lists applications for an operator.
- `POST /v1/operator/issuer-applications/{application_id}/decision` accepts `{decision: "APPROVE" | "REJECT", reason}` from an operator. A reviewed application cannot be decided twice. Decision actor and reason are stored with an audit event.
- Approval yields `APPROVED_PENDING_CHAIN`. It is **not** issuer activation and must not permit key registration or Proof issuance. B/C must agree on the W2 chain-confirmed status and Adapter contract before those actions are connected.

## Shared contract decisions still needed

- A1: final login/account fields, exact browser errors, application form fields and status wording.
- B1/B2 with C3: two Proof payloads, canonical fields, domain/version, binding, `single_use`, lifecycle/reason combinations, and how current chain status is represented. Do not generate new Schema/Golden Fixtures until this is approved.
- B1 with C4 and W2-C1: institution activation/stop state mapping, Adapter errors, chain confirmation and ambiguous-submission recovery.
