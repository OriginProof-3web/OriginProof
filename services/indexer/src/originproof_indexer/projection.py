"""SQLAlchemy event projection; chain state remains authoritative."""

from dataclasses import dataclass

from sqlalchemy import BigInteger, Column, MetaData, String, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
events = Table(
    "chain_events",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("log_index", BigInteger, primary_key=True),
    Column("block_hash", String(66), nullable=False),
    Column("transaction_hash", String(66), nullable=False),
)
checkpoints = Table(
    "chain_checkpoints",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("block_number", BigInteger, nullable=False),
    Column("block_hash", String(66), nullable=False),
)


@dataclass(frozen=True)
class ChainEvent:
    chain_id: int
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

    def checkpoint(self, chain_id):
        with self.engine.connect() as connection:
            row = (
                connection.execute(select(checkpoints).where(checkpoints.c.chain_id == chain_id))
                .mappings()
                .first()
            )
            return None if row is None else (row["block_number"], row["block_hash"])

    def update_checkpoint(self, chain_id, block_number, block_hash):
        if block_number < 0:
            raise ValueError("negative block")
        with self.engine.begin() as connection:
            old = (
                connection.execute(
                    select(checkpoints).where(checkpoints.c.chain_id == chain_id).with_for_update()
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
                    .where(checkpoints.c.chain_id == chain_id)
                    .values(block_number=block_number, block_hash=block_hash)
                )
            else:
                connection.execute(
                    insert(checkpoints).values(
                        chain_id=chain_id, block_number=block_number, block_hash=block_hash
                    )
                )

    def rewind_for_reorg(self, chain_id, safe_block, safe_hash):
        with self.engine.begin() as connection:
            old = (
                connection.execute(
                    select(checkpoints).where(checkpoints.c.chain_id == chain_id).with_for_update()
                )
                .mappings()
                .first()
            )
            if old is None or not 0 <= safe_block <= old["block_number"]:
                raise ValueError("invalid safe ancestor")
            connection.execute(
                delete(events).where(
                    events.c.chain_id == chain_id, events.c.block_number > safe_block
                )
            )
            connection.execute(
                update(checkpoints)
                .where(checkpoints.c.chain_id == chain_id)
                .values(block_number=safe_block, block_hash=safe_hash)
            )
