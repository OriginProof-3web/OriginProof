# Project commands

- `make bootstrap-check`: validate structure and local environment.
- `make demo`: start and seed the MVP end-to-end demo; opens API/web services.
- `make demo-stop`: stop demo services.
- `make mvp-test`: API, analyzer, contracts, integration checks.
- `make lint`, `make typecheck`, `make test`, `make smoke`: standard quality checks.
- `make env-check`, `make env-fingerprint`: host commands + Docker Compose validation and comparison; host forge is optional.
- `make generate`: regenerate JSON Schema and golden fixture artifacts from approved source models.

`make demo-reset` deletes DB volumes: use only an explicitly authorized disposable synthetic environment. `make mvp-test` covers legacy regression, not all finals acceptance criteria. See development plan §15.9 for command limits.

Make targets are the stable root interface; use `uv` and `pnpm` through these targets when possible.
