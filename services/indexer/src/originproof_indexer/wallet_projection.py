"""Deployment-isolated wallet event journal; never authoritative for current validity."""

import json

from sqlalchemy import BigInteger, Column, MetaData, String, Table, delete, insert, select, update

metadata = MetaData()
journal = Table(
    "wallet_events", metadata,
    Column("deployment", String(256), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("log_index", BigInteger, primary_key=True),
    Column("payload", String, nullable=False),
)
cursors = Table(
    "wallet_checkpoints", metadata,
    Column("deployment", String(256), primary_key=True),
    Column("block_number", BigInteger, nullable=False),
    Column("block_hash", String(66), nullable=False),
)


class WalletProjection:
    def __init__(self, engine, rpc):
        self.engine, self.rpc = engine, rpc
        self.deployment = f"{rpc.chain_id}:{rpc.address}:{rpc.deployment_hash}"

    def initialize(self):
        metadata.create_all(self.engine)

    def checkpoint(self):
        with self.engine.connect() as conn:
            row = conn.execute(select(cursors).where(
                cursors.c.deployment == self.deployment,
            )).mappings().first()
            return None if row is None else (row["block_number"], row["block_hash"])

    async def sync(self):
        head = await self.rpc.snapshot()
        previous = self.checkpoint()
        if previous is not None:
            if int(head["number"], 16) < previous[0]:
                raise ValueError("wallet head regressed; retry RPC observation")
            old = await self.rpc.block(hex(previous[0]))
            if old["hash"] != previous[1]:
                raise ValueError("wallet reorg: explicit rewind required")
        start = self.rpc.deployment_block if previous is None else previous[0] + 1
        if start > int(head["number"], 16):
            return 0
        logs = await self.rpc.logs(start, head)
        # Compare-and-swap makes a competing worker roll back its entire page.
        with self.engine.begin() as conn:
            if previous is None:
                conn.execute(insert(cursors).values(
                    deployment=self.deployment, block_number=int(head["number"], 16),
                    block_hash=head["hash"],
                ))
            else:
                changed = conn.execute(update(cursors).where(
                    cursors.c.deployment == self.deployment,
                    cursors.c.block_number == previous[0], cursors.c.block_hash == previous[1],
                ).values(block_number=int(head["number"], 16), block_hash=head["hash"]))
                if changed.rowcount != 1:
                    raise ValueError("concurrent wallet checkpoint change; retry")
            for log in logs:
                conn.execute(insert(journal).values(
                    deployment=self.deployment, block_number=int(log["blockNumber"], 16),
                    log_index=int(log["logIndex"], 16),
                    payload=json.dumps(log, sort_keys=True, separators=(",", ":")),
                ))
        return len(logs)

    async def rewind(self, safe_block, safe_hash):
        if safe_block < self.rpc.deployment_block:
            raise ValueError("safe ancestor predates deployment")
        await self.rpc.snapshot()
        block = await self.rpc.block(hex(safe_block))
        if block["hash"] != safe_hash:
            raise ValueError("safe ancestor hash mismatch")
        old = self.checkpoint()
        if old is None or safe_block > old[0]:
            raise ValueError("invalid safe ancestor")
        # A caller-selected height is not evidence of a common ancestor.
        with self.engine.connect() as conn:
            retained = conn.execute(select(journal).where(
                journal.c.deployment == self.deployment,
                journal.c.block_number <= safe_block,
            )).mappings().all()
        canonical = {}
        for row in retained:
            number = row["block_number"]
            if number not in canonical:
                canonical[number] = await self.rpc.block(hex(number))
            if json.loads(row["payload"])["blockHash"] != canonical[number]["hash"]:
                raise ValueError("safe ancestor retains orphan wallet events")
        await self.rpc.check(block)
        with self.engine.begin() as conn:
            changed = conn.execute(update(cursors).where(
                cursors.c.deployment == self.deployment, cursors.c.block_number == old[0],
                cursors.c.block_hash == old[1],
            ).values(block_number=safe_block, block_hash=block["hash"]))
            if changed.rowcount != 1:
                raise ValueError("concurrent wallet checkpoint change; retry")
            conn.execute(delete(journal).where(
                journal.c.deployment == self.deployment, journal.c.block_number > safe_block,
            ))
