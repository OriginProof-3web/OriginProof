FROM ghcr.io/astral-sh/uv:0.8.17-python3.13-bookworm

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY packages/python/pyproject.toml packages/python/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY services/analyzer/pyproject.toml services/analyzer/pyproject.toml
COPY packages/python packages/python
COPY apps/api apps/api
COPY services/analyzer services/analyzer
COPY services/indexer/src services/indexer/src
COPY scripts/fixtures scripts/fixtures
# 지갑 Registry 연결 검증용: 커밋된 ABI와 배포 기록(*.local.json 은 .dockerignore 로 제외)
COPY packages/contracts/abi packages/contracts/abi
COPY packages/contracts/deployments packages/contracts/deployments
ENV PYTHONPATH=/workspace/apps/api/src:/workspace/packages/python:/workspace/services/indexer/src
RUN uv sync --frozen --no-dev --package originproof-api

CMD ["uv", "run", "--package", "originproof-api", "uvicorn", "originproof_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
