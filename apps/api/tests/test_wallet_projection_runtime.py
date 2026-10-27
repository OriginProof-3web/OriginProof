"""Lifespan wiring of the legacy + wallet event projections (synthetic RPC + SQLite; mock).

The legacy ProofStatusRegistry scan itself needs PostgreSQL (advisory lock); here it is replaced
by a synthetic scan that writes through the real legacy `ProjectionStore`. The live Anvil +
PostgreSQL run of both is in test_wallet_failover_live.py.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from eth_abi import encode
from eth_utils import keccak
from fastapi import HTTPException
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_failover import FailoverWalletRpc
from infrastructure.blockchain.wallet_rpc import signature
from originproof_api import main, projection, readiness
from originproof_api.settings import Settings
from originproof_indexer.projection import PROOF_REGISTERED, ProjectionStore, decode_proof_log
from originproof_indexer.projection import proof_events as legacy_events
from originproof_indexer.wallet_projection import WalletProjection, journal
from sqlalchemy import create_engine, select

ROOT = Path(__file__).resolve().parents[3]
ABI = json.loads((ROOT / "packages/contracts/abi/OriginProofWalletRegistry.json").read_text())
ADDRESS = "0x" + "12" * 20
CODE = b"runtime"
TX = "0x" + "aa" * 32


def block_hash(number):
    return "0x" + f"{number:02x}" * 32


def approved_log(number):
    entry = next(x for x in ABI if x.get("name") == "ProposalApproved" and x["type"] == "event")
    topics, data = ["0x" + keccak(text=signature(entry)).hex()], []
    for field in entry["inputs"]:
        value = {"bytes32": b"x" * 32, "address": "0x" + "34" * 20, "uint8": 1, "uint64": 1}[
            field["type"]
        ]
        if field["indexed"]:
            topics.append("0x" + encode([field["type"]], [value]).hex())
        else:
            data.append((field["type"], value))
    return {
        "address": ADDRESS,
        "topics": topics,
        "data": "0x" + encode([x[0] for x in data], [x[1] for x in data]).hex(),
        "blockNumber": hex(number),
        "blockHash": block_hash(number),
        "transactionHash": TX,
        "logIndex": "0x0",
        "removed": False,
    }


class Node:
    """Deployment at block 1, one ProposalApproved event in every later block."""

    def __init__(self):
        self.head, self.down = 2, False
        self.fork = {}  # 재조직 흉내: 블록 번호 → 바뀐 해시

    def hash(self, number):
        return self.fork.get(number, block_hash(number))

    def handle(self, request):
        if self.down:
            raise httpx.ConnectError("synthetic wallet RPC down", request=request)
        payload = json.loads(request.content)
        method, params = payload["method"], payload["params"]

        def block(tag):
            number = self.head if tag == "latest" else int(tag, 16)
            return {
                "number": hex(number),
                "hash": self.hash(number),
                "timestamp": hex(100 + number),
                "transactions": [TX] if number >= 2 else [],
            }

        result = {
            "eth_chainId": lambda: "0x7a69",
            "eth_getBlockByNumber": lambda: block(params[0]),
            "eth_getCode": lambda: "0x" + CODE.hex(),
            "eth_getLogs": lambda: [
                approved_log(n) | {"blockHash": self.hash(n)}
                for n in range(int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16) + 1)
                if n >= 2
            ],
        }[method]()
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})


LEGACY_DEPLOYMENT = "dep_" + "ab" * 32


class LegacyChain:
    """Synthetic ProofStatusRegistry chain: deployment at block 1, ProofRegistered per block."""

    def __init__(self):
        self.head, self.fail, self.hang = 2, False, False

    def log(self, number):
        return decode_proof_log(
            {
                "topics": [PROOF_REGISTERED, "0x" + f"{number:064x}", "0x" + "01" * 32,
                           "0x" + "02" * 32],
                "data": "0x",
                "blockNumber": hex(number),
                "blockHash": "0x" + f"{number + 100:064x}",
                "transactionHash": "0x" + "bb" * 32,
                "logIndex": "0x0",
            },
            31337,
            LEGACY_DEPLOYMENT,
        )  # fmt: skip

    async def scan(self, engine):
        # The legacy scan runs in its own thread/event loop (asyncio.run), so poll a flag.
        while self.hang:
            await asyncio.sleep(0.05)
        if self.fail:
            raise RuntimeError("synthetic legacy RPC down")
        store = ProjectionStore(engine)
        checkpoint = store.sync_confirmed(
            31337,
            LEGACY_DEPLOYMENT,
            1,
            lambda: self.head,
            lambda number: "0x" + f"{number + 100:064x}",
            lambda number: [self.log(number)] if number >= 2 else [],
        )
        return projection.SyncView(
            status="SYNCED" if checkpoint else "WAITING_CONFIRMATIONS",
            deployment_id=LEGACY_DEPLOYMENT,
            checkpoint_block=checkpoint[0] if checkpoint else None,
            checked_at=datetime.now(UTC),
        )


ISSUERS = ("iss_synthetic_payment", "iss_synthetic_document")


class ReadySession:
    """Just enough of a DB session for check_ready: current revision and prepared accounts."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def scalar(self, query):
        return readiness.REVISION

    async def scalars(self, query):
        return [
            SimpleNamespace(role="operator", issuer_id=None, account_id="acc_op"),
            SimpleNamespace(role="recipient", issuer_id=None, account_id="acc_rcpt"),
            *(
                SimpleNamespace(role="issuer", issuer_id=issuer, account_id=f"acc_{issuer}")
                for issuer in ISSUERS
            ),
        ]


@pytest.fixture
async def wired(tmp_path, monkeypatch):
    node, legacy = Node(), LegacyChain()
    created = []

    class Recording(WalletProjection):
        def __init__(self, engine, rpc, **kwargs):
            super().__init__(engine, rpc, **kwargs)
            created.append(self)

    async def no_cleanup(app, restart):
        return []

    async def no_maintenance(app, stop):
        await stop.wait()

    engine = create_engine("sqlite:///" + str(tmp_path / "wallet.db"))
    ProjectionStore(engine).initialize()
    journal.metadata.create_all(engine)  # 지갑 표도 미리 둔다(지갑 미사용 시 비어 있음 확인용)

    async def legacy_scan(settings):
        return await legacy.scan(engine)

    monkeypatch.setattr(projection, "WalletProjection", Recording)
    monkeypatch.setattr(projection, "scan", legacy_scan)
    monkeypatch.setattr(main, "cleanup", no_cleanup)
    monkeypatch.setattr(main, "maintenance", no_maintenance)

    async def dispose():
        pass

    async def ping():
        pass

    database = SimpleNamespace(
        engine=SimpleNamespace(sync_engine=engine),
        dispose=dispose,
        ping=ping,
        session_factory=ReadySession,
    )
    transport = httpx.MockTransport(node.handle)
    async with httpx.AsyncClient(transport=transport) as client:
        rpc = FailoverWalletRpc(
            client,
            ("http://primary.test",),
            chain_id=31337,
            address=ADDRESS,
            deployment_block=1,
            deployment_hash=block_hash(1),
            runtime_code_hash="0x" + keccak(CODE).hex(),
            abi=ABI,
        )

        def app(enabled=True, connected=True, wallet=True, legacy_manifest=None):
            settings = Settings(
                _env_file=None,
                projection_enabled=enabled,
                projection_poll_seconds=1,
                wallet_registry_address=ADDRESS if wallet else None,
                blockchain_manifest_path=legacy_manifest,
                finals_payment_issuer_id=ISSUERS[0],
                finals_document_issuer_id=ISSUERS[1],
            )
            chain = WalletRegistryReadAdapter(rpc) if connected and wallet else None
            created_app = main.create_app(database=database, settings=settings, wallet_chain=chain)

            async def issuer(*args):
                return None  # readiness 의 기관 조회만 대신한다(이 시험 범위 밖).

            created_app.state.wallet_runtime.rpc = issuer
            return created_app

        yield SimpleNamespace(
            node=node, legacy=legacy, rpc=rpc, created=created, engine=engine, app=app
        )
    engine.dispose()


async def wait_for(app, status, attr="wallet_projection"):
    for _ in range(200):
        if getattr(app.state, attr).status == status:
            return getattr(app.state, attr)
        await asyncio.sleep(0.02)
    pytest.fail(f"{attr} stayed {getattr(app.state, attr)}")


async def ready(app):
    try:
        await readiness.check_ready(app)
    except HTTPException as error:
        assert error.status_code == 503 and error.detail == "RUNTIME_NOT_READY"
        return False
    return True


def legacy_blocks(engine):
    with engine.connect() as conn:
        return sorted(row.block_number for row in conn.execute(select(legacy_events)))


def journal_blocks(engine):
    with engine.connect() as conn:
        return [row.block_number for row in conn.execute(select(journal))]


async def test_enabled_and_connected_projects_confirmed_blocks_with_failover_rpc(wired):
    app = wired.app()
    async with app.router.lifespan_context(app):
        view = await wait_for(app, "SYNCED")
        # 연결된 adapter 의 전환 RPC 인스턴스를 그대로 쓴다.
        assert [store.rpc for store in wired.created] == [app.state.wallet_runtime.chain.rpc]
        assert wired.created[0].rpc is wired.rpc and wired.created[0].confirmations == 2
        # head 2 는 위에 블록이 없어 아직 확정 전: 반영하지 않는다.
        assert view.checkpoint_block == 1 and journal_blocks(wired.engine) == []
        wired.node.head = 4
        for _ in range(150):
            if app.state.wallet_projection.checkpoint_block == 3:
                break
            await asyncio.sleep(0.02)
        assert app.state.wallet_projection.checkpoint_block == 3
        assert journal_blocks(wired.engine) == [2, 3]
        assert app.state.wallet_projection.deployment_id == wired.created[0].deployment
        # 지갑 전용(기존 manifest 없음)이면 기존 projection 은 돌지 않는다(Sepolia 구성).
        assert app.state.projection.status == "DISABLED" and legacy_blocks(wired.engine) == []


async def test_reorg_rewinds_automatically_and_returns_to_synced(wired):
    app = wired.app()
    async with app.router.lifespan_context(app):
        wired.node.head = 4
        for _ in range(150):
            if app.state.wallet_projection.checkpoint_block == 3:
                break
            await asyncio.sleep(0.02)
        assert journal_blocks(wired.engine) == [2, 3]
        # 블록 3·4 재조직: 아직 정본인 블록 2로 자동 되감고 새 블록 3을 다시 반영해야 한다
        wired.node.fork = {3: "0x" + "f3" * 32, 4: "0x" + "f4" * 32}
        for _ in range(200):
            view = app.state.wallet_projection
            if view.status == "SYNCED" and view.checkpoint_hash == "0x" + "f3" * 32:
                break
            await asyncio.sleep(0.02)
        view = app.state.wallet_projection
        assert view.status == "SYNCED" and view.checkpoint_hash == "0x" + "f3" * 32
        with wired.engine.connect() as conn:
            rows = {r.block_number: r.payload for r in conn.execute(select(journal))}
        assert sorted(rows) == [2, 3] and "f3" * 32 in rows[3]
        assert await ready(app)


async def test_disabled_or_unconnected_never_runs_wallet_projection(wired):
    app = wired.app(enabled=False)
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0.1)
        assert app.state.projection.status == "DISABLED"
        assert app.state.wallet_projection.status == "DISABLED"
    app = wired.app(connected=False)
    async with app.router.lifespan_context(app):
        view = await wait_for(app, "RECOVERING")
        assert view.error_code == "PROJECTION_UNAVAILABLE"
    assert wired.created == []


async def test_without_wallet_registry_the_legacy_projection_still_runs(wired):
    app = wired.app(wallet=False)
    async with app.router.lifespan_context(app):
        view = await wait_for(app, "SYNCED", "projection")
        assert view.deployment_id == LEGACY_DEPLOYMENT and view.checkpoint_block == 1
        assert app.state.wallet_projection.status == "DISABLED"
    assert wired.created == [] and journal_blocks(wired.engine) == []


async def test_both_registries_project_their_own_events_and_gate_readiness(wired):
    app = wired.app(legacy_manifest="legacy.json")
    async with app.router.lifespan_context(app):
        await wait_for(app, "SYNCED", "projection")
        await wait_for(app, "SYNCED")
        assert await ready(app)
        wired.node.head = wired.legacy.head = 4
        for _ in range(200):
            if (
                app.state.projection.checkpoint_block == 3
                and app.state.wallet_projection.checkpoint_block == 3
            ):
                break
            await asyncio.sleep(0.02)
        # 각자의 표에 각자의 확정 블록 이벤트만 반영된다.
        assert legacy_blocks(wired.engine) == [2, 3]
        assert journal_blocks(wired.engine) == [2, 3]
        assert app.state.projection.deployment_id == LEGACY_DEPLOYMENT
        assert app.state.wallet_projection.deployment_id == wired.created[0].deployment
        assert await ready(app)

        # 한쪽(지갑) 장애 → not-ready, 기존 쪽은 계속 SYNCED.
        wired.node.down = True
        await wait_for(app, "RECOVERING")
        assert app.state.projection.status == "SYNCED"
        assert not await ready(app)
        wired.node.down = False
        await wait_for(app, "SYNCED")
        assert await ready(app)

        # 한쪽(기존) 장애 → not-ready.
        wired.legacy.fail = True
        await wait_for(app, "RECOVERING", "projection")
        assert app.state.wallet_projection.status == "SYNCED"
        assert not await ready(app)
        wired.legacy.fail = False
        await wait_for(app, "SYNCED", "projection")
        assert await ready(app)

        # 한쪽(기존) 지연: 스캔이 멈춰 poll 3회(3초) 넘게 갱신되지 않으면 STALE → not-ready.
        wired.legacy.hang = True
        await asyncio.sleep(3.3)
        assert app.state.projection.status == "SYNCED"  # 마지막 값은 남지만
        assert not await ready(app)  # 현재 값으로 보지 않는다
        wired.legacy.hang = False
        for _ in range(100):
            if await ready(app):
                break
            await asyncio.sleep(0.05)
        assert await ready(app)


@pytest.mark.parametrize(
    ("legacy", "wallet", "expected"),
    [
        (("SYNCED", 0), ("SYNCED", 0), True),
        (("WAITING_CONFIRMATIONS", 0), ("SYNCED", 0), True),
        (("RECOVERING", 0), ("SYNCED", 0), False),  # 기존 장애
        (("SYNCED", 0), ("RECOVERING", 0), False),  # 지갑 장애
        (("CATCHING_UP", 0), ("SYNCED", 0), False),  # 기존 블록 지연
        (("SYNCED", 4), ("SYNCED", 0), False),  # 기존 갱신 지연(poll 1초 × 3 초과)
        (("SYNCED", 0), ("SYNCED", 4), False),  # 지갑 갱신 지연
        (("SYNCED", 2), ("SYNCED", 2), True),  # 한도 안
        (("STARTING", None), ("SYNCED", 0), False),
        (("SYNCED", 0), ("STARTING", None), False),
    ],
)
async def test_readiness_needs_every_running_projection_current(wired, legacy, wallet, expected):
    app = wired.app(legacy_manifest="legacy.json")

    def view(status, age):
        checked = None if age is None else datetime.now(UTC) - timedelta(seconds=age)
        return projection.SyncView(status=status, checked_at=checked)

    app.state.projection, app.state.wallet_projection = view(*legacy), view(*wallet)
    assert await ready(app) is expected


async def test_wallet_only_readiness_ignores_the_disabled_legacy_view(wired):
    app = wired.app()
    app.state.projection = projection.SyncView(status="DISABLED")
    app.state.wallet_projection = projection.SyncView(status="SYNCED", checked_at=datetime.now(UTC))
    assert await ready(app)
    app.state.wallet_projection = projection.SyncView(status="RECOVERING")
    assert not await ready(app)


async def test_unconfirmed_head_is_not_journaled(tmp_path):
    node = Node()
    engine = create_engine("sqlite:///" + str(tmp_path / "confirm.db"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(node.handle)) as client:
        rpc = FailoverWalletRpc(
            client,
            ("http://primary.test",),
            chain_id=31337,
            address=ADDRESS,
            deployment_block=1,
            deployment_hash=block_hash(1),
            runtime_code_hash="0x" + keccak(CODE).hex(),
            abi=ABI,
        )
        store = WalletProjection(engine, rpc, confirmations=2)
        store.initialize()
        node.head = 1
        assert await store.sync() == 0 and store.checkpoint() is None
        node.head = 2
        assert await store.sync() == 0 and store.checkpoint()[0] == 1
        node.head = 3
        assert await store.sync() == 1 and store.checkpoint()[0] == 2
        assert journal_blocks(engine) == [2]
    engine.dispose()
