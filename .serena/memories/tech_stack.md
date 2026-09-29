# Tech Stack

- Python 3.13 (uv workspace); FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, Redis, Celery.
- Analyzer uses OpenAI Responses API through `LLMProvider`; default `OPENAI_MODEL=gpt-5.6-luna`; Mock provider is default for tests.
- Solidity with Foundry/OpenZeppelin; local Anvil EVM and testnet support. Blockchain state stores issuer/key trust state, never raw proof payloads.
- Web: Next.js 15, React 19, TypeScript; post-MVP surface.
- Docker Compose, Makefile, GitHub Actions. Python lock: `uv.lock`; Node package manager: pnpm 11.19.0; Solidity config under `packages/contracts/foundry.toml`.