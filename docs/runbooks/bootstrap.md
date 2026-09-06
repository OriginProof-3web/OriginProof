# Bootstrap runbook

The Bootstrap PR is created from `bootstrap/mvp-v1`. It must not be committed directly to
`main`.

## Team startup

1. Merge the reviewed Bootstrap PR.
2. Share the exact merge commit SHA.
3. Each member checks out that SHA, copies `.env.example` to `.env`, and runs `make bootstrap`.
4. Each member runs `make env-check`, `make mvp-up`, `make seed`, `make smoke`, and
   `make env-fingerprint`.
5. Compare the `comparable` object in `build/environment_fingerprint.json` before creating an
   MVP feature branch.

## Local reset

`make demo-reset` removes only the named Docker Compose volumes for this project and recreates
the synthetic seed state. It must never be used against production infrastructure.
