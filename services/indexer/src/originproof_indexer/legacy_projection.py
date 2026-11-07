import json
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChainEvent:
    chain_id: int
    block_number: int
    block_hash: str
    transaction_hash: str
    log_index: int
    event_name: str
    payload: dict[str, Any]


class ProjectionStore:
    """Small projection primitive; production can swap SQLite for PostgreSQL."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS processed_chain_events (
                chain_id INTEGER NOT NULL,
                block_number INTEGER NOT NULL,
                block_hash TEXT NOT NULL,
                transaction_hash TEXT NOT NULL,
                log_index INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (chain_id, block_number, log_index)
            );
            CREATE TABLE IF NOT EXISTS chain_checkpoints (
                chain_id INTEGER PRIMARY KEY,
                safe_block_number INTEGER NOT NULL,
                safe_block_hash TEXT NOT NULL
            );
            """
        )

    def apply(self, event: ChainEvent) -> bool:
        """Persist once; returns False when the block/log event was already applied."""
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT OR IGNORE INTO processed_chain_events
                (chain_id, block_number, block_hash, transaction_hash, log_index, event_name,
                 payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.chain_id,
                    event.block_number,
                    event.block_hash,
                    event.transaction_hash,
                    event.log_index,
                    event.event_name,
                    json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
                ),
            )
            return cursor.rowcount == 1

    def update_checkpoint(self, chain_id: int, block_number: int, block_hash: str) -> None:
        with self._connection:
            current = self.checkpoint(chain_id)
            if current is not None and block_number < current[0]:
                raise ValueError("checkpoint cannot move backwards without explicit reorg recovery")
            self._connection.execute(
                """
                INSERT INTO chain_checkpoints (chain_id, safe_block_number, safe_block_hash)
                VALUES (?, ?, ?)
                ON CONFLICT(chain_id) DO UPDATE SET
                    safe_block_number = excluded.safe_block_number,
                    safe_block_hash = excluded.safe_block_hash
                """,
                (chain_id, block_number, block_hash),
            )

    def checkpoint(self, chain_id: int) -> tuple[int, str] | None:
        row = self._connection.execute(
            "SELECT safe_block_number, safe_block_hash FROM chain_checkpoints WHERE chain_id = ?",
            (chain_id,),
        ).fetchone()
        return None if row is None else (int(row[0]), str(row[1]))

    def rewind_for_reorg(self, chain_id: int, last_safe_block: int, block_hash: str) -> None:
        """Delete only projections above a caller-verified safe ancestor."""
        with self._connection:
            self._connection.execute(
                "DELETE FROM processed_chain_events WHERE chain_id = ? AND block_number > ?",
                (chain_id, last_safe_block),
            )
            self._connection.execute(
                """
                INSERT INTO chain_checkpoints (chain_id, safe_block_number, safe_block_hash)
                VALUES (?, ?, ?)
                ON CONFLICT(chain_id) DO UPDATE SET
                    safe_block_number = excluded.safe_block_number,
                    safe_block_hash = excluded.safe_block_hash
                """,
                (chain_id, last_safe_block, block_hash),
            )
