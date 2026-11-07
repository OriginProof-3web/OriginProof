import sqlite3

import pytest
from originproof_indexer.legacy_projection import ChainEvent, ProjectionStore


def event(block: int = 10, log_index: int = 0) -> ChainEvent:
    return ChainEvent(31337, block, f"0xblock{block}", "0xtx", log_index, "IssuerRegistered", {})


def test_event_identity_is_chain_block_and_log_index() -> None:
    store = ProjectionStore(sqlite3.connect(":memory:"))
    store.initialize()
    assert store.apply(event())
    assert not store.apply(event())
    assert store.apply(event(log_index=1))


def test_checkpoint_survives_new_store_instance() -> None:
    connection = sqlite3.connect(":memory:")
    first = ProjectionStore(connection)
    first.initialize()
    first.update_checkpoint(31337, 10, "0x10")
    assert ProjectionStore(connection).checkpoint(31337) == (10, "0x10")


def test_checkpoint_cannot_silently_move_backwards() -> None:
    store = ProjectionStore(sqlite3.connect(":memory:"))
    store.initialize()
    store.update_checkpoint(31337, 10, "0x10")
    with pytest.raises(ValueError, match="cannot move backwards"):
        store.update_checkpoint(31337, 9, "0x09")


def test_explicit_reorg_recovery_rewinds_projection() -> None:
    connection = sqlite3.connect(":memory:")
    store = ProjectionStore(connection)
    store.initialize()
    store.apply(event(10))
    store.apply(event(11))
    store.update_checkpoint(31337, 11, "0x11")
    store.rewind_for_reorg(31337, 10, "0x10")
    count = connection.execute("SELECT COUNT(*) FROM processed_chain_events").fetchone()[0]
    assert count == 1
    assert store.checkpoint(31337) == (10, "0x10")
