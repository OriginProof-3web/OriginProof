"""Deployment-isolated wallet event journal; never authoritative for current validity."""

import json
from functools import partial

from sqlalchemy import BigInteger, Column, MetaData, String, Table, delete, insert, select, update

LOG_CHUNK_SIZE = 200

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


async def direct(fn):
    return fn()


class WalletProjection:
    def __init__(self, engine, rpc, *, run=direct, confirmations=1):
        # run(fn) executes the synchronous DB callback fn; the API passes SQLAlchemy's
        # greenlet_spawn so an asyncpg engine's sync_engine works. confirmations=2 keeps the
        # last block out until it has one block on top (same rule as the legacy projection).
        if type(confirmations) is not int or confirmations < 1:
            raise ValueError("invalid confirmations")
        self.engine, self.rpc, self.run, self.confirmations = engine, rpc, run, confirmations
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
        if self.confirmations > 1:
            confirmed = int(head["number"], 16) - self.confirmations + 1
            if confirmed < self.rpc.deployment_block:
                return 0
            head = await self.rpc.block(hex(confirmed))
        previous = await self.run(self.checkpoint)
        if previous is not None:
            if int(head["number"], 16) < previous[0]:
                raise ValueError("wallet head regressed; retry RPC observation")
            old = await self.rpc.block(hex(previous[0]))
            if old["hash"] != previous[1]:
                raise ValueError("wallet reorg: explicit rewind required")
        start = self.rpc.deployment_block if previous is None else previous[0] + 1
        confirmed = int(head["number"], 16)
        count = 0
        while start <= confirmed:
            end = min(start + LOG_CHUNK_SIZE - 1, confirmed)
            chunk_head = await self.rpc.block(hex(end))
            logs = await self.rpc.logs(start, chunk_head)
            await self.run(partial(self._store, previous, chunk_head, logs))
            previous = (int(chunk_head["number"], 16), chunk_head["hash"])
            count += len(logs)
            start = end + 1
        return count

    def _store(self, previous, head, logs):
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

    async def rewind(self, safe_block, safe_hash):
        if safe_block < self.rpc.deployment_block:
            raise ValueError("safe ancestor predates deployment")
        await self.rpc.snapshot()
        block = await self.rpc.block(hex(safe_block))
        if block["hash"] != safe_hash:
            raise ValueError("safe ancestor hash mismatch")
        old = await self.run(self.checkpoint)
        if old is None or safe_block > old[0]:
            raise ValueError("invalid safe ancestor")

        # A caller-selected height is not evidence of a common ancestor.
        def retained_rows():
            with self.engine.connect() as conn:
                return conn.execute(select(journal).where(
                    journal.c.deployment == self.deployment,
                    journal.c.block_number <= safe_block,
                )).mappings().all()

        retained = await self.run(retained_rows)
        canonical = {}
        for row in retained:
            number = row["block_number"]
            if number not in canonical:
                canonical[number] = await self.rpc.block(hex(number))
            if json.loads(row["payload"])["blockHash"] != canonical[number]["hash"]:
                raise ValueError("safe ancestor retains orphan wallet events")
        await self.rpc.check(block)

        def move():
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

        await self.run(move)

    async def recover_reorg(self):
        """Rewind to the newest stored event block that is still canonical, else deployment.

        A canonical block hash commits to every earlier block, so a stored event block whose
        hash still matches is a verified common ancestor; rewind() re-checks retained events.
        """
        old = await self.run(self.checkpoint)
        if old is None:
            return None

        def stored_blocks():
            with self.engine.connect() as conn:
                return [row[0] for row in conn.execute(
                    select(journal.c.block_number).where(
                        journal.c.deployment == self.deployment,
                        journal.c.block_number <= old[0],
                    ).distinct().order_by(journal.c.block_number.desc())
                )]

        for number in await self.run(stored_blocks):
            if number < self.rpc.deployment_block:
                break
            try:
                block = await self.rpc.block(hex(number))
                await self.rewind(number, block["hash"])
                return number, block["hash"]
            except ValueError:
                continue  # orphaned or mismatched; try an older stored block
        await self.rewind(self.rpc.deployment_block, self.rpc.deployment_hash)
        return self.rpc.deployment_block, self.rpc.deployment_hash
