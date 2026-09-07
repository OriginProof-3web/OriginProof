import pytest
from originproof_indexer import ChainEvent, ProjectionStore
from sqlalchemy import create_engine


def event(block=1, block_hash="0x01"):
    return ChainEvent(31337, block, 0, block_hash, "0xtx")


def test_restart_replay(tmp_path):
    url = "sqlite:///" + str(tmp_path / "projection.db")
    engine = create_engine(url)
    store = ProjectionStore(engine)
    store.initialize()
    assert store.apply(event())
    store.update_checkpoint(31337, 1, "0x01")
    engine.dispose()
    reopened = create_engine(url)
    try:
        store = ProjectionStore(reopened)
        assert store.checkpoint(31337) == (1, "0x01")
        assert not store.apply(event())
    finally:
        reopened.dispose()


def test_reorg_and_conflicts():
    engine = create_engine("sqlite://")
    try:
        store = ProjectionStore(engine)
        store.initialize()
        store.apply(event())
        store.apply(event(2, "0x02"))
        store.update_checkpoint(31337, 2, "0x02")
        with pytest.raises(ValueError):
            store.apply(event(2, "0xff"))
        with pytest.raises(ValueError):
            store.update_checkpoint(31337, 1, "0x01")
        with pytest.raises(ValueError):
            store.update_checkpoint(31337, 2, "0xff")
        store.rewind_for_reorg(31337, 1, "0x01")
        assert store.checkpoint(31337) == (1, "0x01")
        assert store.apply(event(2, "0xff"))
        assert not store.apply(event())
        with pytest.raises(ValueError):
            store.rewind_for_reorg(31337, 3, "0x03")
    finally:
        engine.dispose()
