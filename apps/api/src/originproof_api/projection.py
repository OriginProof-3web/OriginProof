"""C runtime orchestration of B's atomic projection. Current validity stays with Reader."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from infrastructure.blockchain import JsonRpcBlockchainReader
from infrastructure.blockchain.manifest import load_manifest, validate_hash
from originproof_core import DependencyUnavailableError
from originproof_indexer.projection import (
    PROOF_CONSUMED,
    PROOF_REGISTERED,
    PROOF_REVOKED,
    ProjectionStore,
    decode_proof_log,
)
from originproof_indexer.wallet_projection import WalletProjection
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.util import greenlet_spawn

from .accounts import current_session
from .database import Database

router = APIRouter(tags=["operations"])


class SyncView(BaseModel):
    status: str = "STARTING"
    deployment_id: str | None = None
    checkpoint_block: int | None = None
    checkpoint_hash: str | None = None
    checked_at: datetime | None = None
    error_code: str | None = None
    authority: str = "HISTORICAL_EVENTS_ONLY"


async def verified_rpc_url(settings, manifest):
    """First CHAIN_TARGET RPC (primary, then fallback) that passes B Reader identity checks."""
    for url in settings.blockchain_rpc_urls:
        reader = JsonRpcBlockchainReader(
            url,
            settings.blockchain_manifest_path,
            issuer_ids=[settings.blockchain_issuer_id],
            expected_chain_id=manifest.chain_id,
        )
        try:
            # B Reader validates chain/genesis/deployment/code before scanning this environment.
            await reader.get_issuer(settings.blockchain_issuer_id)
        except DependencyUnavailableError:
            continue
        return url
    raise DependencyUnavailableError("projection RPC unavailable")


async def scan(settings):
    """Run in a worker thread: live synchronous callbacks + asyncpg greenlet DB bridge."""
    database = Database(settings.database_url)
    try:
        manifest = load_manifest(settings.blockchain_manifest_path, settings.blockchain_chain_id)
        rpc_url = await verified_rpc_url(settings, manifest)
        reader = JsonRpcBlockchainReader(
            rpc_url,
            settings.blockchain_manifest_path,
            issuer_ids=[settings.blockchain_issuer_id],
            expected_chain_id=manifest.chain_id,
        )
        # B Reader validates chain/deployment/code before scanning this environment.
        await reader.get_issuer(settings.blockchain_issuer_id)
        with httpx.Client(timeout=5) as client:

            def rpc(method, params):
                response = client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": params,
                    },
                )
                response.raise_for_status()
                body = response.json()
                if body.get("id") != 1 or "error" in body or "result" not in body:
                    raise ValueError("projection RPC unavailable")
                return body["result"]

            def block_hash(number):
                return validate_hash(rpc("eth_getBlockByNumber", [hex(number), False])["hash"])

            def logs(number):
                raw = rpc(
                    "eth_getLogs",
                    [
                        {
                            "address": manifest.contract("ProofStatusRegistry").address,
                            "fromBlock": hex(number),
                            "toBlock": hex(number),
                            "topics": [[PROOF_REGISTERED, PROOF_REVOKED, PROOF_CONSUMED]],
                        }
                    ],
                )
                return sorted(
                    [
                        decode_proof_log(log, manifest.chain_id, manifest.deployment_id)
                        for log in raw
                    ],
                    key=lambda log: log.event.log_index,
                )

            async with database.engine.connect() as connection:
                # ponytail: one scanner across local workers; shard by deployment if needed.
                await connection.execute(text("SELECT pg_advisory_xact_lock(741031338)"))
                store = ProjectionStore(database.engine.sync_engine)
                prior = await connection.run_sync(
                    lambda _: store.checkpoint(manifest.chain_id, manifest.deployment_id)
                )
                # ponytail: bounded 200-block poll; full historical backfill uses repeated polls.
                ceiling = (prior[0] if prior else manifest.deployment_block - 1) + 201
                checkpoint = await connection.run_sync(
                    lambda _: store.sync_confirmed(
                        manifest.chain_id,
                        manifest.deployment_id,
                        manifest.deployment_block,
                        lambda: min(int(rpc("eth_blockNumber", []), 16), ceiling),
                        block_hash,
                        logs,
                    )
                )
            actual_tip = int(rpc("eth_blockNumber", []), 16)
        return SyncView(
            status=("SYNCED" if checkpoint[0] >= actual_tip - 1 else "CATCHING_UP")
            if checkpoint
            else "WAITING_CONFIRMATIONS",
            deployment_id=manifest.deployment_id,
            checkpoint_block=checkpoint[0] if checkpoint else None,
            checkpoint_hash=checkpoint[1] if checkpoint else None,
            checked_at=datetime.now(UTC),
        )
    finally:
        await database.dispose()


class WalletScan:
    """New Registry events through the connected adapter's (failover) RPC; never authority."""

    def __init__(self, app):
        self.app, self.store = app, None

    async def __call__(self):
        runtime = self.app.state.wallet_runtime
        if runtime.chain is None and runtime.connect is not None:
            runtime.chain = await runtime.connect()
        rpc = getattr(runtime.chain, "rpc", None)
        if rpc is None:
            raise DependencyUnavailableError("wallet registry not connected")
        if self.store is None or self.store.rpc is not rpc:
            self.store = WalletProjection(
                self.app.state.database.engine.sync_engine,
                rpc,
                run=greenlet_spawn,
                confirmations=2,
            )
            await greenlet_spawn(self.store.initialize)
        # sync() always reaches the confirmed tip, so a checkpoint means SYNCED.
        await self.store.sync()
        checkpoint = await greenlet_spawn(self.store.checkpoint)
        return SyncView(
            status="SYNCED" if checkpoint else "WAITING_CONFIRMATIONS",
            deployment_id=self.store.deployment,
            checkpoint_block=checkpoint[0] if checkpoint else None,
            checkpoint_hash=checkpoint[1] if checkpoint else None,
            checked_at=datetime.now(UTC),
        )


def legacy_projection_enabled(settings):
    """ProofStatusRegistry projection keeps running as before; only a wallet-only deployment
    without a legacy manifest (Sepolia) skips it."""
    return settings.projection_enabled and (
        not settings.wallet_registry_address or bool(settings.blockchain_manifest_path)
    )


def wallet_projection_enabled(settings):
    return settings.projection_enabled and bool(settings.wallet_registry_address)


def current(view, settings):
    """A view not refreshed within three polls is STALE, never current."""
    if view.checked_at and (datetime.now(UTC) - view.checked_at).total_seconds() > (
        settings.projection_poll_seconds * 3
    ):
        return view.model_copy(update={"status": "STALE", "error_code": "PROJECTION_STALE"})
    return view


def running_views(app):
    """Current view of every projection this runtime runs (legacy first, then wallet)."""
    settings = app.state.settings
    views = []
    if legacy_projection_enabled(settings):
        views.append(app.state.projection)
    if wallet_projection_enabled(settings):
        views.append(app.state.wallet_projection)
    return [current(view, settings) for view in views]


async def run_projection(app, stop, scan_once=None, attr="projection"):
    async def legacy():
        return await asyncio.to_thread(lambda: asyncio.run(scan(app.state.settings)))

    scan_once = scan_once or legacy
    while not stop.is_set():
        try:
            setattr(app.state, attr, await scan_once())
        except Exception:
            # Retain last checkpoint for diagnostics, never present its status as current.
            setattr(
                app.state,
                attr,
                getattr(app.state, attr).model_copy(
                    update={
                        "status": "RECOVERING",
                        "error_code": "PROJECTION_UNAVAILABLE",
                        "checked_at": datetime.now(UTC),
                    }
                ),
            )
        try:
            await asyncio.wait_for(stop.wait(), timeout=app.state.settings.projection_poll_seconds)
        except TimeoutError:
            pass


@router.get("/v1/chain-sync", response_model=SyncView)
async def sync_status(request: Request, identity: Annotated[tuple, Depends(current_session)]):
    account, _ = identity
    if account.role not in ("operator", "issuer") or (
        account.role == "issuer" and not account.issuer_id
    ):
        raise HTTPException(403, "FORBIDDEN")
    # Legacy view when the legacy projection runs (unchanged); wallet view for wallet-only.
    views = running_views(request.app)
    return views[0] if views else current(request.app.state.projection, request.app.state.settings)
