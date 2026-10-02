"""SQLAlchemy event projection; chain state remains authoritative."""

from dataclasses import dataclass

from Crypto.Hash import keccak
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
processed_blocks = Table(
    "chain_processed_blocks",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("block_hash", String(66), nullable=False),
)
proof_events = Table(
    "proof_chain_events",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("log_index", BigInteger, primary_key=True),
    Column("proof_id_hash", String(66), nullable=False),
    Column("event_type", String(16), nullable=False),
)


@dataclass(frozen=True)
class ChainEvent:
    chain_id: int
    deployment_id: str
    block_number: int
    log_index: int
    block_hash: str
    transaction_hash: str


@dataclass(frozen=True)
class ProofLog:
    event: ChainEvent
    proof_id_hash: str
    event_type: str


def _topic(signature):
    return "0x" + keccak.new(digest_bits=256, data=signature.encode()).hexdigest()


PROOF_REGISTERED = _topic("ProofRegistered(bytes32,bytes32,bytes32)")
PROOF_REVOKED = _topic("ProofRevoked(bytes32,uint64)")
PROOF_CONSUMED = _topic("ProofConsumed(bytes32,uint8,uint64)")


def decode_proof_log(raw, chain_id, deployment_id):
    """Decode the three ProofStatusRegistry events without storing private fields."""

    topics = raw["topics"]
    data = raw["data"]
    if not isinstance(topics, list) or not topics or not isinstance(data, str):
        raise ValueError("invalid proof log")
    signature = topics[0].lower()
    event_type = {
        PROOF_REGISTERED: "REGISTERED",
        PROOF_REVOKED: "REVOKED",
        PROOF_CONSUMED: "CONSUMED",
    }.get(signature)
    expected_topics = 4 if event_type == "REGISTERED" else 2
    expected_data = {"REGISTERED": 0, "REVOKED": 64, "CONSUMED": 128}.get(event_type)
    if event_type is None or len(topics) != expected_topics or len(data) != expected_data + 2:
        raise ValueError("invalid proof event signature or shape")
    for value in [*topics, raw["blockHash"], raw["transactionHash"]]:
        if not isinstance(value, str) or len(value) != 66 or not value.startswith("0x"):
            raise ValueError("invalid proof log hash")
        int(value[2:], 16)
    if not data.startswith("0x"):
        raise ValueError("invalid proof event data")
    int(data[2:] or "0", 16)
    if event_type == "CONSUMED" and int(data[2:66], 16) not in (0, 1):
        raise ValueError("invalid consume actor kind")
    event = ChainEvent(
        chain_id,
        deployment_id,
        int(raw["blockNumber"], 16),
        int(raw["logIndex"], 16),
        raw["blockHash"].lower(),
        raw["transactionHash"].lower(),
    )
    return ProofLog(event, topics[1].lower(), event_type)


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

    def apply_proof_log(self, log: ProofLog) -> bool:
        event = log.event
        if min(event.chain_id, event.block_number, event.log_index) < 0:
            raise ValueError("negative event position")
        self._deployment_id(event.deployment_id)
        if log.event_type not in ("REGISTERED", "REVOKED", "CONSUMED"):
            raise ValueError("invalid proof event type")
        if len(log.proof_id_hash) != 66 or not log.proof_id_hash.startswith("0x"):
            raise ValueError("invalid proof id hash")
        int(log.proof_id_hash[2:], 16)
        key = (event.chain_id, event.deployment_id, event.block_number, event.log_index)
        values = dict(
            zip(("chain_id", "deployment_id", "block_number", "log_index"), key, strict=True)
        )
        proof_values = values | {"proof_id_hash": log.proof_id_hash, "event_type": log.event_type}
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(events).values(**vars(event)))
                connection.execute(insert(proof_events).values(**proof_values))
            return True
        except IntegrityError:
            with self.engine.connect() as connection:
                old_event = (
                    connection.execute(
                        select(events).where(
                            events.c.chain_id == key[0],
                            events.c.deployment_id == key[1],
                            events.c.block_number == key[2],
                            events.c.log_index == key[3],
                        )
                    )
                    .mappings()
                    .first()
                )
                old_proof = (
                    connection.execute(
                        select(proof_events).where(
                            proof_events.c.chain_id == key[0],
                            proof_events.c.deployment_id == key[1],
                            proof_events.c.block_number == key[2],
                            proof_events.c.log_index == key[3],
                        )
                    )
                    .mappings()
                    .first()
                )
            if (
                old_event is None
                or dict(old_event) != vars(event)
                or old_proof is None
                or dict(old_proof) != proof_values
            ):
                raise ValueError(
                    "conflicting proof event: explicit reorg recovery required"
                ) from None
            return False

    def apply_block(self, chain_id, deployment_id, block_number, block_hash, logs=()):
        """Atomically persist an ordered block, its logs, and checkpoint."""

        logs = tuple(logs)
        self._deployment_id(deployment_id)
        if (
            type(chain_id) is not int
            or chain_id < 0
            or type(block_number) is not int
            or block_number < 0
        ):
            raise ValueError("invalid block position")
        if (
            not isinstance(block_hash, str)
            or len(block_hash) != 66
            or not block_hash.startswith("0x")
        ):
            raise ValueError("invalid block hash")
        int(block_hash[2:], 16)
        block_hash = block_hash.lower()
        positions = []
        for item in logs:
            event = item.event if isinstance(item, ProofLog) else item
            if not isinstance(event, ChainEvent) or (
                event.chain_id,
                event.deployment_id,
                event.block_number,
                event.block_hash.lower(),
            ) != (chain_id, deployment_id, block_number, block_hash):
                raise ValueError("log does not belong to block")
            if isinstance(item, ProofLog) and item.event_type not in (
                "REGISTERED",
                "REVOKED",
                "CONSUMED",
            ):
                raise ValueError("invalid proof event type")
            if isinstance(item, ProofLog) and (
                not isinstance(item.proof_id_hash, str)
                or len(item.proof_id_hash) != 66
                or not item.proof_id_hash.startswith("0x")
            ):
                raise ValueError("invalid proof id hash")
            if isinstance(item, ProofLog):
                int(item.proof_id_hash[2:], 16)
            positions.append(event.log_index)
        if positions != sorted(set(positions)) or any(position < 0 for position in positions):
            raise ValueError("logs must be in unique chain order")

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
            if old is not None and block_number <= old["block_number"]:
                seen = connection.execute(
                    select(processed_blocks.c.block_hash).where(
                        processed_blocks.c.chain_id == chain_id,
                        processed_blocks.c.deployment_id == deployment_id,
                        processed_blocks.c.block_number == block_number,
                    )
                ).scalar_one_or_none()
                if seen != block_hash:
                    raise ValueError("replayed block differs or lacks recorded hash")
                return False
            if old is not None and block_number != old["block_number"] + 1:
                raise ValueError("block gap")
            connection.execute(
                insert(processed_blocks).values(
                    chain_id=chain_id,
                    deployment_id=deployment_id,
                    block_number=block_number,
                    block_hash=block_hash,
                )
            )
            for item in logs:
                event = item.event if isinstance(item, ProofLog) else item
                connection.execute(insert(events).values(**vars(event)))
                if isinstance(item, ProofLog):
                    connection.execute(
                        insert(proof_events).values(
                            chain_id=chain_id,
                            deployment_id=deployment_id,
                            block_number=block_number,
                            log_index=event.log_index,
                            proof_id_hash=item.proof_id_hash,
                            event_type=item.event_type,
                        )
                    )
            if old is None:
                connection.execute(
                    insert(checkpoints).values(
                        chain_id=chain_id,
                        deployment_id=deployment_id,
                        block_number=block_number,
                        block_hash=block_hash,
                    )
                )
            else:
                connection.execute(
                    update(checkpoints)
                    .where(
                        checkpoints.c.chain_id == chain_id,
                        checkpoints.c.deployment_id == deployment_id,
                    )
                    .values(block_number=block_number, block_hash=block_hash)
                )
        return True

    def projected_proof_status(self, chain_id, deployment_id, proof_id_hash):
        """Historical event projection only; live authorization uses Reader."""

        self._deployment_id(deployment_id)
        with self.engine.connect() as connection:
            row = connection.execute(
                select(proof_events.c.event_type)
                .where(
                    proof_events.c.chain_id == chain_id,
                    proof_events.c.deployment_id == deployment_id,
                    proof_events.c.proof_id_hash == proof_id_hash,
                )
                .order_by(proof_events.c.block_number.desc(), proof_events.c.log_index.desc())
                .limit(1)
            ).first()
        return (
            None
            if row is None
            else {"REGISTERED": "ACTIVE", "REVOKED": "REVOKED", "CONSUMED": "CONSUMED"}[row[0]]
        )

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
            tracked = connection.execute(
                select(processed_blocks.c.block_number)
                .where(
                    processed_blocks.c.chain_id == chain_id,
                    processed_blocks.c.deployment_id == deployment_id,
                )
                .limit(1)
            ).first()
            if tracked is not None:
                raise ValueError("tracked blocks require atomic apply_block")
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

    def rewind_for_reorg(self, chain_id, deployment_id, safe_block, safe_hash, block_hash_at):
        self._deployment_id(deployment_id)
        if block_hash_at(safe_block) != safe_hash:
            raise ValueError("safe ancestor is not canonical")
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
            recorded = connection.execute(
                select(processed_blocks.c.block_hash).where(
                    processed_blocks.c.chain_id == chain_id,
                    processed_blocks.c.deployment_id == deployment_id,
                    processed_blocks.c.block_number == safe_block,
                )
            ).scalar_one_or_none()
            if recorded != safe_hash:
                raise ValueError("safe ancestor differs from stored block or is untracked")
            connection.execute(
                delete(proof_events).where(
                    proof_events.c.chain_id == chain_id,
                    proof_events.c.deployment_id == deployment_id,
                    proof_events.c.block_number > safe_block,
                )
            )
            connection.execute(
                delete(events).where(
                    events.c.chain_id == chain_id,
                    events.c.deployment_id == deployment_id,
                    events.c.block_number > safe_block,
                )
            )
            connection.execute(
                delete(processed_blocks).where(
                    processed_blocks.c.chain_id == chain_id,
                    processed_blocks.c.deployment_id == deployment_id,
                    processed_blocks.c.block_number > safe_block,
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

    def recover_reorg(self, chain_id, deployment_id, block_hash_at):
        """Rewind only to a stored block that still matches the canonical chain."""

        self._deployment_id(deployment_id)
        with self.engine.connect() as connection:
            candidates = connection.execute(
                select(processed_blocks.c.block_number, processed_blocks.c.block_hash)
                .where(
                    processed_blocks.c.chain_id == chain_id,
                    processed_blocks.c.deployment_id == deployment_id,
                )
                .order_by(processed_blocks.c.block_number.desc())
            ).all()
        if not candidates:
            raise ValueError("no recorded blocks; rebuild from deployment required")
        for number, stored_hash in candidates:
            if block_hash_at(number) == stored_hash:
                self.rewind_for_reorg(chain_id, deployment_id, number, stored_hash, block_hash_at)
                return number, stored_hash
        raise ValueError("no verified common ancestor; rebuild from deployment required")
