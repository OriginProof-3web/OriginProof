"""Runtime primary → fallback switching for wallet Registry reads.

Wraps one WalletRpc per CHAIN_TARGET URL without changing WalletRpc behaviour:

- a read that fails on the primary (connection, timeout, wrong chain/deployment/code) is
  retried on the fallback, but only after the fallback itself passes `snapshot()` (chain ID,
  deployment block hash, runtime code hash). Unverified fallback answers are never returned.
- after a fallback success, reads stay on the fallback for `fallback_seconds`, then the
  primary is tried first again.
- submissions use the primary only. An unconfirmed send is never re-sent to another node;
  Operation recovery decides what happened.
- both failing raises DependencyUnavailableError (API 503). Logs and errors name roles only.
"""

from __future__ import annotations

import logging
import time

from originproof_core import DependencyUnavailableError

from .errors import BlockchainConfigurationError, BlockchainDependencyError
from .wallet_rpc import WalletRpc, _CallReverted

FALLBACK_SECONDS = 60
ROLE = ("primary", "fallback")
# Raw JSON-RPC methods safe to repeat on another node. Anything else is primary-only.
READ_METHODS = frozenset({
    "eth_blockNumber", "eth_call", "eth_chainId", "eth_getBlockByNumber", "eth_getCode",
    "eth_getLogs", "eth_getTransactionByHash", "eth_getTransactionReceipt",
})
logger = logging.getLogger(__name__)
# httpx logs every request URL at INFO ("HTTP Request: POST <url>") and httpcore logs the host at
# DEBUG; a provider URL carries its API key in the path. Neither library logs at WARNING or
# above, so capping both here keeps RPC URLs out of logs even when the root logger is at DEBUG.
for _transport_logger in ("httpx", "httpcore"):
    logging.getLogger(_transport_logger).setLevel(logging.WARNING)


class FailoverWalletRpc:
    def __init__(self, client, rpc_urls, *, clock=time.monotonic,
                 fallback_seconds=FALLBACK_SECONDS, **deployment):
        if not 1 <= len(rpc_urls) <= 2:
            raise BlockchainConfigurationError("one primary and at most one fallback RPC")
        self.endpoints = [WalletRpc(client, url, **deployment) for url in rpc_urls]
        self.clock, self.fallback_seconds = clock, fallback_seconds
        self.fallback_until = None

    def __getattr__(self, name):
        # Deployment identity, ABI tables and pure helpers (pin, decode_log) are identical on
        # both endpoints; take them from the primary.
        if name == "endpoints":
            raise AttributeError(name)
        return getattr(self.endpoints[0], name)

    @property
    def on_fallback(self):
        return self.fallback_until is not None and self.clock() < self.fallback_until

    async def _read(self, method, *args):
        active = self.on_fallback
        for index in (1, 0) if active else (0, 1):
            if index >= len(self.endpoints):
                continue
            endpoint = self.endpoints[index]
            try:
                if index == 1 and not active:
                    await endpoint.snapshot()  # verify the fallback before trusting it
                    # Record the switch as soon as the fallback is verified, so a request budget
                    # cancelled mid-call does not make the next request wait on the primary again.
                    self.fallback_until = self.clock() + self.fallback_seconds
                    logger.warning("wallet RPC switched to fallback for %ss", self.fallback_seconds)
                result = await getattr(endpoint, method)(*args)
            except _CallReverted:
                raise  # a contract answer, not an endpoint failure
            except BlockchainDependencyError:
                logger.warning("wallet RPC %s failed", ROLE[index])
                if index == 1:
                    self.fallback_until = None
                continue
            if index == 0 and self.fallback_until is not None:
                self.fallback_until = None
                logger.info("wallet RPC back on primary")
            return result
        raise DependencyUnavailableError("wallet RPC primary and fallback unavailable")

    async def rpc(self, method, params):
        if method in READ_METHODS:
            return await self._read("rpc", method, params)
        try:
            return await self.endpoints[0].rpc(method, params)
        except BlockchainDependencyError:
            pass  # raised below, outside the handler, so no URL-bearing context is chained
        logger.warning("wallet RPC primary submission failed; not re-sent")
        raise DependencyUnavailableError("wallet RPC primary unavailable")

    async def block(self, number):
        return await self._read("block", number)

    async def snapshot(self):
        return await self._read("snapshot")

    async def check(self, block):
        return await self._read("check", block)

    async def read(self, name, args):
        return await self._read("read", name, args)

    async def call(self, name, args, block):
        return await self._read("call", name, args, block)

    async def logs(self, start, block):
        return await self._read("logs", start, block)

    async def transaction_evidence(self, tx_hash):
        return await self._read("transaction_evidence", tx_hash)
