"""SQLAlchemy event projection; chain state remains authoritative."""

from dataclasses import dataclass

from sqlalchemy import BigInteger, Column, MetaData, String, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
events = Table(
    "chain_events",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("log_index", BigInteger, primary_key=True),
    Column("block_hash", String(66), nullable=False),
    Column("transaction_hash", String(66), nullable=False),
)
checkpoints = Table(
    "chain_checkpoints",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, nullable=False),
    Column("block_hash", String(66), nullable=False),
)


@dataclass(frozen=True)
class ChainEvent:
    chain_id: int
    deployment_id: str
    block_number: int
    log_index: int
    block_hash: str
    transaction_hash: str


class ProjectionStore:
    def __init__(self, engine):
        self.engine = engine

    def initialize(self):
        metadata.create_all(self.engine)

    def apply(self, event: ChainEvent) -> bool:
        values = vars(event)
        if min(event.chain_id, event.block_number, event.log_index) < 0:
            raise ValueError("negative event position")
        self._deployment_id(event.deployment_id)
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(events).values(**values))
            return True
        except IntegrityError:
            with self.engine.connect() as connection:
                old = (
                    connection.execute(
                        select(events).where(
                            events.c.chain_id == event.chain_id,
                            events.c.deployment_id == event.deployment_id,
                            events.c.block_number == event.block_number,
                            events.c.log_index == event.log_index,
                        )
                    )
                    .mappings()
                    .first()
                )
            if old is None or dict(old) != values:
                raise ValueError("conflicting event: explicit reorg recovery required") from None
            return False

    @staticmethod
    def _deployment_id(value):
        if not isinstance(value, str) or len(value) != 68 or not value.startswith("dep_"):
            raise ValueError("invalid deployment id")
        try:
            int(value[4:], 16)
        except ValueError:
            raise ValueError("invalid deployment id") from None
        return value

    def checkpoint(self, chain_id, deployment_id):
        self._deployment_id(deployment_id)
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(checkpoints).where(
                        checkpoints.c.chain_id == chain_id,
                        checkpoints.c.deployment_id == deployment_id,
                    )
                )
                .mappings()
                .first()
            )
            return None if row is None else (row["block_number"], row["block_hash"])

    def verified_checkpoint(self, chain_id, deployment_id, block_hash_at):
        checkpoint = self.checkpoint(chain_id, deployment_id)
        if checkpoint is None:
            return None
        block_number, block_hash = checkpoint
        if block_hash_at(block_number) != block_hash:
            raise ValueError("checkpoint is not on the current deployment chain")
        return checkpoint

    def update_checkpoint(self, chain_id, deployment_id, block_number, block_hash):
        self._deployment_id(deployment_id)
        if block_number < 0:
            raise ValueError("negative block")
        with self.engine.begin() as connection:
            old = (
                connection.execute(
                    select(checkpoints)
                    .where(
                        checkpoints.c.chain_id == chain_id,
                        checkpoints.c.deployment_id == deployment_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if old is not None:
                if block_number < old["block_number"] or (
                    block_number == old["block_number"] and block_hash != old["block_hash"]
                ):
                    raise ValueError("checkpoint conflict: explicit rewind required")
                connection.execute(
                    update(checkpoints)
                    .where(
                        checkpoints.c.chain_id == chain_id,
                        checkpoints.c.deployment_id == deployment_id,
                    )
                    .values(block_number=block_number, block_hash=block_hash)
                )
            else:
                connection.execute(
                    insert(checkpoints).values(
                        chain_id=chain_id,
                        block_number=block_number,
                        block_hash=block_hash,
                        deployment_id=deployment_id,
                    )
                )

    def rewind_for_reorg(self, chain_id, deployment_id, safe_block, safe_hash):
        self._deployment_id(deployment_id)
        with self.engine.begin() as connection:
            old = (
                connection.execute(
                    select(checkpoints)
                    .where(
                        checkpoints.c.chain_id == chain_id,
                        checkpoints.c.deployment_id == deployment_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if old is None or not 0 <= safe_block <= old["block_number"]:
                raise ValueError("invalid safe ancestor")
            connection.execute(
                delete(events).where(
                    events.c.chain_id == chain_id,
                    events.c.deployment_id == deployment_id,
                    events.c.block_number > safe_block,
                )
            )
            connection.execute(
                update(checkpoints)
                .where(
                    checkpoints.c.chain_id == chain_id,
                    checkpoints.c.deployment_id == deployment_id,
                )
                .values(block_number=safe_block, block_hash=safe_hash)
            )
