FROM ghcr.io/foundry-rs/foundry:v1.4.4@sha256:9584dfbb0e2e9bda80332b66a7cebed635fc9786638871df6b7594e39e678578 AS foundry

FROM ghcr.io/astral-sh/uv:0.8.17-python3.13-bookworm

COPY --from=foundry /usr/local/bin/forge /usr/local/bin/forge
COPY --from=foundry /usr/local/bin/cast /usr/local/bin/cast

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY packages/python/pyproject.toml packages/python/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY services/analyzer/pyproject.toml services/analyzer/pyproject.toml
COPY packages/python packages/python
COPY apps/api apps/api
COPY packages/contracts packages/contracts
COPY fixtures fixtures

RUN uv sync --frozen --no-dev --package originproof-api \
    && cd packages/contracts \
    && git init \
    && forge install OpenZeppelin/openzeppelin-contracts@v5.7.0 foundry-rs/forge-std@v1.16.2 \
    && forge build
