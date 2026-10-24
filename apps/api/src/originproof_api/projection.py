"""C runtime orchestration of B's atomic projection. Current validity stays with Reader."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from infrastructure.blockchain import JsonRpcBlockchainReader
from infrastructure.blockchain.manifest import load_manifest, validate_hash
from originproof_indexer.projection import (
    PROOF_CONSUMED,
    PROOF_REGISTERED,
    PROOF_REVOKED,
    ProjectionStore,
    decode_proof_log,
)
from pydantic import BaseModel
from sqlalchemy import text

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


async def scan(settings):
    """Run in a worker thread: live synchronous callbacks + asyncpg greenlet DB bridge."""
    database = Database(settings.database_url)
    try:
        manifest = load_manifest(settings.blockchain_manifest_path, settings.blockchain_chain_id)
        reader = JsonRpcBlockchainReader(
            settings.blockchain_rpc_url,
            settings.blockchain_manifest_path,
            issuer_ids=[settings.blockchain_issuer_id],
            expected_chain_id=manifest.chain_id,
        )
        # B Reader validates chain/deployment/code before scanning this environment.
        await reader.get_issuer(settings.blockchain_issuer_id)
        with httpx.Client(timeout=5) as client:

            def rpc(method, params):
                response = client.post(
                    settings.blockchain_rpc_url,
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


async def run_projection(app, stop):
    while not stop.is_set():
        try:
            app.state.projection = await asyncio.to_thread(
                lambda: asyncio.run(scan(app.state.settings))
            )
        except Exception:
            # Retain last checkpoint for diagnostics, never present its status as current.
            app.state.projection = app.state.projection.model_copy(
                update={
                    "status": "RECOVERING",
                    "error_code": "PROJECTION_UNAVAILABLE",
                    "checked_at": datetime.now(UTC),
                }
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
    view = request.app.state.projection
    if view.checked_at and (datetime.now(UTC) - view.checked_at).total_seconds() > (
        request.app.state.settings.projection_poll_seconds * 3
    ):
        return view.model_copy(update={"status": "STALE", "error_code": "PROJECTION_STALE"})
    return view
