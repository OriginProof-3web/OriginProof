"""CHAIN_TARGET selection shared by API, projection/indexer and the wallet deploy wrapper.

No RPC calls or secrets here. Error messages never echo an RPC URL (it may carry a provider key).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEPLOYMENTS = Path(__file__).resolve().parents[5] / "packages/contracts/deployments"
MODEL_NOTICE = "모델(실제 기관 아님)"
APPROVER_NODES = (
    {
        "role": "approver_1",
        "label": "승인 노드 #1 공공·도메인 검증원(KISA 모델)",
        "notice": MODEL_NOTICE,
    },
    {
        "role": "approver_2",
        "label": "승인 노드 #2 금융·산업 자율규제원(금융보안원 모델)",
        "notice": MODEL_NOTICE,
    },
    {
        "role": "approver_3",
        "label": "승인 노드 #3 통신·인프라 보안컨소시엄",
        "notice": MODEL_NOTICE,
    },
)
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1", "anvil")


@dataclass(frozen=True)
class ChainTarget:
    name: str
    chain_id: int
    default_rpc_url: str | None
    wallet_manifest: str

    @property
    def wallet_manifest_path(self) -> Path:
        return DEPLOYMENTS / self.wallet_manifest


CHAIN_TARGETS = {
    "anvil": ChainTarget("anvil", 31337, "http://127.0.0.1:8545", "31337.wallet.local.json"),
    "sepolia": ChainTarget("sepolia", 11155111, None, "11155111.wallet.json"),
}


def chain_target(value: str | None) -> ChainTarget:
    if value is None:
        return CHAIN_TARGETS["anvil"]
    try:
        return CHAIN_TARGETS[value]
    except (KeyError, TypeError):
        raise ValueError(
            f"CHAIN_TARGET must be one of: {', '.join(CHAIN_TARGETS)} (got {value!r})"
        ) from None


def rpc_urls(target: ChainTarget, primary: str | None, fallback: str | None = None):
    """Ordered (primary, fallback?) RPC URLs. Callers try them in order; fallback is optional."""
    primary = primary or target.default_rpc_url
    if not primary:
        raise ValueError(f"CHAIN_TARGET={target.name} requires a primary RPC URL")
    urls = (primary,) if not fallback else (primary, fallback)
    for kind, url in zip(("primary", "fallback"), urls, strict=False):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError(f"invalid {kind} RPC URL")
        if target.name == "anvil" and parsed.hostname not in LOCAL_HOSTS:
            raise ValueError(f"CHAIN_TARGET=anvil requires a local {kind} RPC URL")
        if target.name == "sepolia" and parsed.scheme != "https":
            raise ValueError(f"CHAIN_TARGET=sepolia requires an https {kind} RPC URL")
    if len(urls) == 2 and urls[0] == urls[1]:
        raise ValueError("fallback RPC URL must differ from the primary")
    return urls
