import pytest
from originproof_indexer import ChainEvent, ProjectionStore, decode_proof_log
from originproof_indexer.projection import PROOF_CONSUMED, PROOF_REGISTERED, PROOF_REVOKED
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


def test_proof_projection_restart_replay_and_rewind(tmp_path):
    proof = "0x" + "11" * 32

    def raw(block, topic, data="0x"):
        topics = [topic, proof]
        if topic == PROOF_REGISTERED:
            topics += ["0x" + "22" * 32, "0x" + "33" * 32]
        return {
            "topics": topics,
            "data": data,
            "blockNumber": hex(block),
            "logIndex": "0x0",
            "blockHash": "0x" + f"{block:064x}",
            "transactionHash": "0x" + f"{block + 100:064x}",
        }

    url = "sqlite:///" + str(tmp_path / "proof-projection.db")
    engine = create_engine(url)
    store = ProjectionStore(engine)
    store.initialize()
    registered = decode_proof_log(raw(1, PROOF_REGISTERED), 31337, DEPLOYMENT)
    assert store.apply_proof_log(registered)
    assert not store.apply_proof_log(registered)
    assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "ACTIVE"
    consumed = decode_proof_log(
        raw(2, PROOF_CONSUMED, "0x" + f"{1:064x}" + f"{150:064x}"),
        31337,
        DEPLOYMENT,
    )
    assert store.apply_proof_log(consumed)
    store.update_checkpoint(31337, DEPLOYMENT, 2, consumed.event.block_hash)
    engine.dispose()

    reopened = create_engine(url)
    try:
        store = ProjectionStore(reopened)
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "CONSUMED"
        assert not store.apply_proof_log(consumed)
        with pytest.raises(ValueError, match="conflicting proof event"):
            store.apply_proof_log(
                decode_proof_log(raw(2, PROOF_REVOKED, "0x" + f"{150:064x}"), 31337, DEPLOYMENT)
            )
        store.rewind_for_reorg(31337, DEPLOYMENT, 1, registered.event.block_hash)
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "ACTIVE"
        revoked = decode_proof_log(raw(2, PROOF_REVOKED, "0x" + f"{151:064x}"), 31337, DEPLOYMENT)
        assert store.apply_proof_log(revoked)
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "REVOKED"
    finally:
        reopened.dispose()


def test_proof_projection_rejects_unknown_event():
    raw = {
        "topics": ["0x" + "00" * 32, "0x" + "11" * 32],
        "data": "0x",
        "blockNumber": "0x1",
        "logIndex": "0x0",
        "blockHash": "0x" + "22" * 32,
        "transactionHash": "0x" + "33" * 32,
    }
    with pytest.raises(ValueError, match="signature"):
        decode_proof_log(raw, 31337, DEPLOYMENT)
