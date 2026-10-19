import pytest
from originproof_indexer import ChainEvent, ProjectionStore, ProofLog, decode_proof_log
from originproof_indexer.projection import PROOF_CONSUMED, PROOF_REGISTERED, PROOF_REVOKED
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

DEPLOYMENT = "dep_" + "1" * 64
REDEPLOYMENT = "dep_" + "2" * 64


def event(block=1, block_hash="0x01", deployment_id=DEPLOYMENT):
    return ChainEvent(31337, deployment_id, block, 0, block_hash, "0xtx")


def block_hash(number):
    return "0x" + f"{number:064x}"


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
        store.apply_block(31337, DEPLOYMENT, 1, block_hash(1), [event(1, block_hash(1))])
        store.apply_block(31337, DEPLOYMENT, 2, block_hash(2), [event(2, block_hash(2))])
        with pytest.raises(ValueError):
            store.apply(event(2, "0xff"))
        with pytest.raises(ValueError):
            store.update_checkpoint(31337, DEPLOYMENT, 1, "0x01")
        with pytest.raises(ValueError):
            store.update_checkpoint(31337, DEPLOYMENT, 2, "0xff")
        store.rewind_for_reorg(31337, DEPLOYMENT, 1, block_hash(1), lambda _: block_hash(1))
        assert store.checkpoint(31337, DEPLOYMENT) == (1, block_hash(1))
        assert store.apply(event(2, "0xff"))
        assert not store.apply(event(1, block_hash(1)))
        with pytest.raises(ValueError):
            store.rewind_for_reorg(31337, DEPLOYMENT, 3, block_hash(3), block_hash)
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
    assert store.apply_block(31337, DEPLOYMENT, 1, registered.event.block_hash, [registered])
    assert not store.apply_proof_log(registered)
    assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "ACTIVE"
    consumed = decode_proof_log(
        raw(2, PROOF_CONSUMED, "0x" + f"{1:064x}" + f"{150:064x}"),
        31337,
        DEPLOYMENT,
    )
    assert store.apply_block(31337, DEPLOYMENT, 2, consumed.event.block_hash, [consumed])
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
        store.rewind_for_reorg(
            31337,
            DEPLOYMENT,
            1,
            registered.event.block_hash,
            lambda _: registered.event.block_hash,
        )
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


def test_atomic_block_replay_restart_and_failed_write(tmp_path):
    url = "sqlite:///" + str(tmp_path / "atomic.db")
    engine = create_engine(url)
    store = ProjectionStore(engine)
    store.initialize()
    first = event(1, block_hash(1))
    assert store.apply_block(31337, DEPLOYMENT, 1, block_hash(1), iter([first]))
    assert not store.apply(first)
    assert not store.apply_block(31337, DEPLOYMENT, 1, block_hash(1), [first])
    assert store.apply_block(31337, DEPLOYMENT, 2, block_hash(2))
    assert store.checkpoint(31337, DEPLOYMENT) == (2, block_hash(2))
    with pytest.raises(ValueError, match="tracked blocks"):
        store.update_checkpoint(31337, DEPLOYMENT, 3, block_hash(3))
    with pytest.raises(ValueError, match="block gap"):
        store.apply_block(31337, DEPLOYMENT, 4, block_hash(4))
    with pytest.raises(ValueError, match="replayed block differs"):
        store.apply_block(31337, DEPLOYMENT, 2, block_hash(9))
    assert store.apply(event(3, block_hash(3)))
    with pytest.raises(IntegrityError):
        store.apply_block(31337, DEPLOYMENT, 3, block_hash(3), [event(3, block_hash(3))])
    assert store.checkpoint(31337, DEPLOYMENT) == (2, block_hash(2))
    engine.dispose()
    reopened = create_engine(url)
    try:
        store = ProjectionStore(reopened)
        assert store.apply_block(31337, DEPLOYMENT, 3, block_hash(3))
        assert store.checkpoint(31337, DEPLOYMENT) == (3, block_hash(3))
    finally:
        reopened.dispose()


def test_reorg_requires_verified_common_ancestor(tmp_path):
    proof = "0x" + "11" * 32
    engine = create_engine("sqlite:///" + str(tmp_path / "fork.db"))
    try:
        store = ProjectionStore(engine)
        store.initialize()
        for number, kind in ((1, "REGISTERED"), (2, "CONSUMED")):
            log = ProofLog(
                event(number, block_hash(number)),
                proof,
                kind,
            )
            store.apply_block(31337, DEPLOYMENT, number, block_hash(number), [log])
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "CONSUMED"
        with pytest.raises(ValueError, match="canonical"):
            store.rewind_for_reorg(
                31337,
                DEPLOYMENT,
                2,
                block_hash(2),
                lambda _: block_hash(9),
            )
        with pytest.raises(ValueError, match="no verified common ancestor"):
            store.recover_reorg(31337, DEPLOYMENT, lambda _: block_hash(9))

        def offline_hash(_number):
            raise ConnectionError("RPC outage")

        with pytest.raises(ConnectionError, match="RPC outage"):
            store.recover_reorg(31337, DEPLOYMENT, offline_hash)
        assert store.checkpoint(31337, DEPLOYMENT) == (2, block_hash(2))
        assert store.recover_reorg(
            31337,
            DEPLOYMENT,
            lambda number: block_hash(1) if number == 1 else block_hash(9),
        ) == (1, block_hash(1))
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "ACTIVE"
        assert store.apply_block(31337, DEPLOYMENT, 2, block_hash(9))
        assert store.checkpoint(31337, DEPLOYMENT) == (2, block_hash(9))
    finally:
        engine.dispose()


def test_confirmed_scan_skips_tip_and_recovers_fork(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "confirmed.db"))
    proof = "0x" + "11" * 32
    hashes = {number: block_hash(number) for number in range(1, 6)}
    chain = {"tip": 3}
    logs = {
        1: [ProofLog(event(1, hashes[1]), proof, "REGISTERED")],
        3: [ProofLog(event(3, hashes[3]), proof, "CONSUMED")],
    }
    try:
        store = ProjectionStore(engine)
        store.initialize()

        def sync():
            return store.sync_confirmed(
                31337,
                DEPLOYMENT,
                1,
                lambda: chain["tip"],
                hashes.__getitem__,
                lambda number: logs.get(number, ()),
            )

        assert sync() == (2, hashes[2])
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "ACTIVE"
        chain["tip"] = 4
        assert sync() == (3, hashes[3])
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "CONSUMED"
        hashes[3] = block_hash(9)
        logs[3] = [ProofLog(event(3, hashes[3]), proof, "REVOKED")]
        with pytest.raises(ValueError, match="current deployment chain"):
            store.verified_projected_proof_status(
                31337,
                DEPLOYMENT,
                proof,
                3,
                hashes.__getitem__,
            )
        assert sync() == (3, hashes[3])
        assert store.projected_proof_status(31337, DEPLOYMENT, proof) == "REVOKED"
        assert (
            store.verified_projected_proof_status(
                31337,
                DEPLOYMENT,
                proof,
                3,
                hashes.__getitem__,
            )
            == "REVOKED"
        )
        with pytest.raises(ValueError, match="not confirmed"):
            store.verified_projected_proof_status(
                31337,
                DEPLOYMENT,
                proof,
                2,
                hashes.__getitem__,
            )
        assert sync() == (3, hashes[3])
    finally:
        engine.dispose()


def test_confirmed_scan_rpc_error_and_moving_head_do_not_advance(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "unstable.db"))
    hashes = {number: block_hash(number) for number in range(1, 5)}
    chain = {"tip": 3, "fail": False}
    try:
        store = ProjectionStore(engine)
        store.initialize()

        def logs_at(number):
            if chain["fail"] and number == 3:
                raise ConnectionError("RPC outage")
            return ()

        def sync():
            return store.sync_confirmed(
                31337,
                DEPLOYMENT,
                1,
                lambda: chain["tip"],
                hashes.__getitem__,
                logs_at,
            )

        assert sync() == (2, hashes[2])
        chain.update(tip=4, fail=True)
        with pytest.raises(ConnectionError, match="RPC outage"):
            sync()
        assert store.checkpoint(31337, DEPLOYMENT) == (2, hashes[2])
        chain["fail"] = False
        assert sync() == (3, hashes[3])
        chain["tip"] = 3
        with pytest.raises(ValueError, match="outside confirmed"):
            sync()
        assert store.checkpoint(31337, DEPLOYMENT) == (3, hashes[3])
    finally:
        engine.dispose()
