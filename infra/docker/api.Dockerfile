FROM ghcr.io/astral-sh/uv:0.8.17-python3.13-bookworm

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY packages/python/pyproject.toml packages/python/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY services/analyzer/pyproject.toml services/analyzer/pyproject.toml
COPY packages/python packages/python
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package originproof-api

CMD ["uv", "run", "--package", "originproof-api", "uvicorn", "originproof_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
