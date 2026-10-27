"""Production wiring for the wallet Registry read adapter.

The deploy wrapper (`packages/contracts/script/deploy_wallet_registry.py`) writes a manifest;
this module turns that manifest into a verified `WalletRegistryReadAdapter`:

- the manifest must be for the configured chain and the configured Registry address,
- the committed ABI must match the manifest `abi_sha256`,
- `from_deployment` re-checks the canonical CREATE, creation bytecode, runtime code hash and
  the fixed 2-of-3 approver set on chain before anything is injected.

RPC URLs are tried primary → fallback at connect time only. Nothing here logs a URL.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import httpx

from .errors import BlockchainConfigurationError
from .manifest import validate_address, validate_hash
from .wallet_adapter import WalletRegistryReadAdapter
from .wallet_creation import WalletCreationProof

NAME = "OriginProofWalletRegistry"
ABI_PATH = Path(__file__).resolve().parents[5] / f"packages/contracts/abi/{NAME}.json"
RETRY_SECONDS = 15
ROLE = ("primary", "fallback")
logger = logging.getLogger(__name__)


def _hex(value, what):
    if not isinstance(value, str) or not value.startswith("0x") or len(value) % 2:
        raise BlockchainConfigurationError(f"wallet manifest {what} is not hex")
    try:
        return bytes.fromhex(value[2:])
    except ValueError as exc:
        raise BlockchainConfigurationError(f"wallet manifest {what} is not hex") from exc


def load_wallet_deployment(manifest_path, *, chain_id, address, abi_path=None):
    """Return (WalletRpc deployment kwargs, WalletCreationProof); raise on bad config."""
    path = Path(manifest_path)
    try:
        manifest = json.loads(path.read_text())
        abi_raw = Path(abi_path or ABI_PATH).read_bytes()
    except (OSError, ValueError) as exc:
        raise BlockchainConfigurationError("wallet manifest or ABI unreadable") from exc
    try:
        contract = manifest["contracts"][NAME]
        if manifest["chain_id"] != chain_id:
            raise BlockchainConfigurationError("wallet manifest is for another chain")
        if validate_address(contract["address"]) != validate_address(address):
            raise BlockchainConfigurationError("wallet manifest address differs from settings")
        if hashlib.sha256(abi_raw).hexdigest() != contract["abi_sha256"]:
            raise BlockchainConfigurationError("committed ABI differs from the deployed ABI")
        if "runtime_code_hash" not in manifest or "creation_bytecode" not in manifest:
            raise BlockchainConfigurationError(
                "wallet manifest lacks runtime_code_hash/creation_bytecode; "
                "re-record it with deploy_wallet_registry.py --deployment-tx"
            )
        runtime_code_hash = validate_hash(manifest["runtime_code_hash"])
        creation = _hex(manifest["creation_bytecode"], "creation_bytecode")
        deployment = {
            "chain_id": chain_id,
            "address": validate_address(contract["address"]),
            "deployment_block": int(manifest["deployment_block"]),
            "deployment_hash": validate_hash(manifest["deployment_block_hash"]),
            "runtime_code_hash": runtime_code_hash,
            "abi": json.loads(abi_raw),
        }
        proof = WalletCreationProof(validate_hash(contract["deployment_tx"]).lower(), creation)
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, BlockchainConfigurationError):
            raise
        raise BlockchainConfigurationError("invalid wallet manifest") from exc
    return deployment, proof


class WalletRegistryConnector:
    """Connect once at startup and retry lazily (throttled) while the chain is unreachable."""

    def __init__(self, client: httpx.AsyncClient, settings, *, clock=time.monotonic):
        self.client, self.settings, self.clock = client, settings, clock
        self.next_attempt = 0.0
        self.rpc_index = None

    async def __call__(self):
        if self.clock() < self.next_attempt:
            return None
        self.next_attempt = self.clock() + RETRY_SECONDS
        settings = self.settings
        try:
            deployment, proof = load_wallet_deployment(
                settings.wallet_manifest_path,
                chain_id=settings.blockchain_chain_id,
                address=settings.wallet_registry_address,
            )
        except BlockchainConfigurationError as exc:
            logger.error("wallet registry not connected: %s", exc)
            return None
        for index, url in enumerate(settings.blockchain_rpc_urls):
            try:
                adapter = await WalletRegistryReadAdapter.from_deployment(
                    self.client, url, creation_proof=proof, **deployment
                )
            except Exception:  # noqa: BLE001 - any failure leaves the API fail-closed (503)
                logger.warning("wallet registry RPC %s unavailable", ROLE[min(index, 1)])
                continue
            self.rpc_index = index
            logger.info("wallet registry connected via %s RPC", ROLE[min(index, 1)])
            return adapter
        return None
