import pytest
from originproof_indexer import ChainEvent, ProjectionStore
from sqlalchemy import create_engine

DEPLOYMENT = "dep_" + "1" * 64
REDEPLOYMENT = "dep_" + "2" * 64


def event(block=1, block_hash="0x01", deployment_id=DEPLOYMENT):
    return ChainEvent(31337, deployment_id, block, 0, block_hash, "0xtx")


def test_restart_replay(tmp_path):
    url = "sqlite:///" + str(tmp_path / "projection.db")
    engine = create_engine(url)
    store = ProjectionStore(engine)
    store.initialize()
    assert store.apply(event())
    store.update_checkpoint(31337, DEPLOYMENT, 1, "0x01")
    engine.dispose()
    reopened = create_engine(url)
    try:
        store = ProjectionStore(reopened)
        assert store.checkpoint(31337, DEPLOYMENT) == (1, "0x01")
        assert store.verified_checkpoint(31337, DEPLOYMENT, lambda _: "0x01") == (
            1,
            "0x01",
        )
        assert not store.apply(event())
        with pytest.raises(ValueError, match="current deployment chain"):
            store.verified_checkpoint(31337, DEPLOYMENT, lambda _: "0xff")
    finally:
        reopened.dispose()


def test_reorg_and_conflicts():
    engine = create_engine("sqlite://")
    try:
        store = ProjectionStore(engine)
        store.initialize()
        store.apply(event())
        store.apply(event(2, "0x02"))
        store.update_checkpoint(31337, DEPLOYMENT, 2, "0x02")
        with pytest.raises(ValueError):
            store.apply(event(2, "0xff"))
        with pytest.raises(ValueError):
            store.update_checkpoint(31337, DEPLOYMENT, 1, "0x01")
        with pytest.raises(ValueError):
            store.update_checkpoint(31337, DEPLOYMENT, 2, "0xff")
        store.rewind_for_reorg(31337, DEPLOYMENT, 1, "0x01")
        assert store.checkpoint(31337, DEPLOYMENT) == (1, "0x01")
        assert store.apply(event(2, "0xff"))
        assert not store.apply(event())
        with pytest.raises(ValueError):
            store.rewind_for_reorg(31337, DEPLOYMENT, 3, "0x03")
    finally:
        engine.dispose()


def test_redeployment_isolated_from_previous_projection():
    engine = create_engine("sqlite://")
    try:
        store = ProjectionStore(engine)
        store.initialize()
        assert store.apply(event())
        assert store.apply(event(deployment_id=REDEPLOYMENT))
        store.update_checkpoint(31337, DEPLOYMENT, 1, "0x01")
        store.update_checkpoint(31337, REDEPLOYMENT, 1, "0xaa")
        assert store.checkpoint(31337, DEPLOYMENT) == (1, "0x01")
        assert store.checkpoint(31337, REDEPLOYMENT) == (1, "0xaa")
    finally:
        engine.dispose()
