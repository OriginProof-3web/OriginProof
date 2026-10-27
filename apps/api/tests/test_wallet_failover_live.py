"""Opt-in: runtime RPC failover and both projections on a disposable Anvil + PostgreSQL.

One Anvil sits behind two local TCP proxies (primary, fallback) so both endpoints serve the same
chain state. The API is started through create_app lifespan with only settings; the primary proxy
is then cut while the API runs. Checks: reads continue through the verified fallback, new
Registry events reach PostgreSQL through the projection, the primary is used again after the
fallback window, and a fallback on another chain is refused. The legacy Issuer/Key/ProofStatus
registries are deployed on the same Anvil (manifest in tmp_path only) so the legacy projection
runs next to the wallet projection and both write their own events to PostgreSQL. Anvil's
unlocked default accounts sign (no key is read or printed). Run with ORIGINPROOF_WALLET_LIVE=1
(anvil, forge, docker and a local postgres:16.4-alpine image required; nothing is pulled).
"""

import asyncio
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from eth_abi import encode
from eth_utils import keccak
from infrastructure.blockchain.network import chain_target
from infrastructure.blockchain.wallet_deployment import load_wallet_deployment
from infrastructure.blockchain.wallet_failover import FailoverWalletRpc
from infrastructure.blockchain.wallet_recovery import calldata
from infrastructure.blockchain.wallet_rpc import hex_bytes, named
from originproof_core import DependencyUnavailableError
from originproof_core.wallet_contract import GovernanceProposal, KeyProofMessage, WalletDomain
from originproof_core.wallet_signatures import identifier_hash, proposal_id, typed_data
from originproof_indexer.projection import metadata as legacy_metadata
from originproof_indexer.projection import proof_events
from originproof_indexer.wallet_projection import journal
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "packages/contracts"
NAME = "OriginProofWalletRegistry"

LEGACY = ("IssuerRegistry", "IssuerKeyRegistry", "ProofStatusRegistry")

pytestmark = pytest.mark.skipif(
    os.environ.get("ORIGINPROOF_WALLET_LIVE") != "1",
    reason="disposable wallet EVM opt-in",
)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def load_wrapper():
    spec = spec_from_file_location(
        "deploy_wallet_registry", CONTRACTS / "script/deploy_wallet_registry.py"
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Proxy:
    """Local TCP forwarder; stop() refuses new and drops open connections like a dead node."""

    def __init__(self, target):
        self.target, self.port, self.server, self.requests, self.open = target, 0, None, 0, set()

    async def start(self):
        self.server = await asyncio.start_server(self.accept, "127.0.0.1", self.port)
        self.port = self.server.sockets[0].getsockname()[1]

    async def accept(self, reader, writer):
        try:
            up_reader, up_writer = await asyncio.open_connection("127.0.0.1", self.target)
        except OSError:
            writer.close()
            return
        self.open |= {writer, up_writer}

        async def pipe(source, sink, count):
            try:
                while data := await source.read(65536):
                    if count:
                        self.requests += data.count(b"POST ")
                    sink.write(data)
                    await sink.drain()
            except (ConnectionError, OSError):
                pass
            finally:
                sink.close()

        await asyncio.gather(pipe(reader, up_writer, True), pipe(up_reader, writer, False))

    async def stop(self):
        self.server.close()
        for writer in self.open:
            writer.close()
        self.open.clear()
        await asyncio.wait_for(self.server.wait_closed(), 5)


def start_anvil(port):
    return subprocess.Popen(
        ["anvil", "--host", "127.0.0.1", "--port", str(port), "--chain-id", "31337", "--silent"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def test_runtime_failover_keeps_reads_and_projection_on_live_chain(tmp_path, monkeypatch):
    assert shutil.which("anvil") and shutil.which("forge") and shutil.which("docker"), (
        "ORIGINPROOF_WALLET_LIVE=1 requires anvil, forge and docker"
    )
    await asyncio.to_thread(
        subprocess.run, ["forge", "build"], cwd=CONTRACTS, check=True, capture_output=True
    )
    artifact = json.loads((CONTRACTS / f"out/{NAME}.sol/{NAME}.json").read_text())
    anvil_port, other_port, pg_port = free_port(), free_port(), free_port()
    anvil_url = f"http://127.0.0.1:{anvil_port}"
    container = "originproof-failover-live-" + uuid4().hex[:12]
    anvil = other = None
    proxies = []
    try:
        subprocess.run(
            ["docker", "run", "-d", "--pull", "never", "--name", container,
             "--label", "originproof.validation=true", "--tmpfs", "/var/lib/postgresql/data",
             "-p", f"127.0.0.1:{pg_port}:5432", "-e", "POSTGRES_USER=originproof",
             "-e", "POSTGRES_PASSWORD=originproof", "-e", "POSTGRES_DB=originproof",
             "postgres:16.4-alpine"],
            check=True, capture_output=True,
        )  # fmt: skip
        anvil = start_anvil(anvil_port)
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:

            async def rpc(method, params, url=anvil_url):
                response = await client.post(
                    url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
                )
                body = response.json()
                assert "error" not in body, f"disposable RPC rejected {method}"
                return body["result"]

            for _ in range(100):
                try:
                    assert await rpc("eth_chainId", []) == "0x7a69"
                    break
                except httpx.TransportError:
                    await asyncio.sleep(0.05)
            else:
                pytest.fail("disposable Anvil did not start")
            for _ in range(100):
                ready = subprocess.run(
                    ["docker", "exec", container, "pg_isready", "-h", "127.0.0.1", "-U", "originproof"],
                    capture_output=True,
                )
                if ready.returncode == 0:
                    break
                await asyncio.sleep(0.1)
            else:
                pytest.fail("disposable PostgreSQL did not start")

            async def mined(tx_hash):
                for _ in range(100):
                    receipt = await rpc("eth_getTransactionReceipt", [tx_hash])
                    if receipt is not None:
                        assert receipt["status"] == "0x1"
                        return receipt
                    await asyncio.sleep(0.05)
                pytest.fail("disposable transaction was not mined")

            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
            # Deploy exactly like the wrapper expects (creation bytecode + approvers), then let
            # the wrapper's own manifest builder verify it. The manifest stays in tmp_path.
            accounts = await rpc("eth_accounts", [])
            approvers, institution = accounts[1:4], accounts[4]
            creation = hex_bytes(artifact["bytecode"]["object"]) + encode(
                ["address[3]"], [approvers]
            )
            deploy_tx = await rpc(
                "eth_sendTransaction",
                [{"from": accounts[0], "data": "0x" + creation.hex(), "gas": "0xc00000"}],
            )
            await mined(deploy_tx)
            wrapper = load_wrapper()
            manifest = wrapper.build_manifest(
                wrapper.rpc_caller(anvil_url), chain_target("anvil"), CONTRACTS, deploy_tx,
                approvers, sha.strip(),
            )  # fmt: skip
            manifest_path = tmp_path / "31337.wallet.json"
            manifest_path.write_text(json.dumps(manifest))
            address = manifest["contracts"][NAME]["address"]

            # 기존 Registry 3종: 기존 배포 스크립트와 같은 생성자·초기 역할(관리자가 기관/키 관리
            # 역할을 가진 상태)로 Anvil 잠금 해제 계정이 직접 배포한다. deployments/ 는 쓰지 않는다.
            admin, issuer_manager, key_manager, issuer_account, gateway = accounts[5:10]

            async def create(name, types, values):
                built = json.loads((CONTRACTS / f"out/{name}.sol/{name}.json").read_text())
                code = hex_bytes(built["bytecode"]["object"]) + encode(types, values)
                tx_hash = await rpc(
                    "eth_sendTransaction",
                    [{"from": admin, "data": "0x" + code.hex(), "gas": "0xc00000"}],
                )
                receipt = await mined(tx_hash)
                return receipt["contractAddress"], int(receipt["blockNumber"], 16)

            async def transact(sender, to, signature, types, values):
                data = keccak(text=signature)[:4] + encode(types, values)
                tx_hash = await rpc(
                    "eth_sendTransaction",
                    [{"from": sender, "to": to, "data": "0x" + data.hex(), "gas": "0x800000"}],
                )
                return int((await mined(tx_hash))["blockNumber"], 16)

            issuers, first_block = await create("IssuerRegistry", ["address"], [admin])
            keys, _ = await create("IssuerKeyRegistry", ["address", "address"], [admin, issuers])
            proofs, _ = await create(
                "ProofStatusRegistry",
                ["address", "address", "address", "address"],
                [admin, gateway, issuers, keys],
            )
            legacy_issuer = keccak(text="iss_origin_mock_bank")
            legacy_key = keccak(text="key_failover_live_legacy")
            chain_now = int((await rpc("eth_getBlockByNumber", ["latest", False]))["timestamp"], 16)
            await transact(admin, issuers, "registerIssuer(bytes32,address,bytes32)",
                           ["bytes32", "address", "bytes32"],
                           [legacy_issuer, issuer_account, keccak(text="synthetic")])  # fmt: skip
            await transact(admin, keys, "registerKey(bytes32,bytes32,address,uint64,uint64)",
                           ["bytes32", "bytes32", "address", "uint64", "uint64"],
                           [legacy_key, legacy_issuer, accounts[4], chain_now - 60,
                            chain_now + 10**6])  # fmt: skip

            async def register_proof(label):
                proof_id = keccak(text=label)
                block = await transact(
                    gateway, proofs,
                    "registerProof(bytes32,bytes32,bytes32,bytes32,bytes32,uint64,uint64,bool)",
                    ["bytes32", "bytes32", "bytes32", "bytes32", "bytes32", "uint64", "uint64",
                     "bool"],
                    [proof_id, legacy_issuer, legacy_key, keccak(text=label + "-digest"),
                     keccak(text=label + "-binding"), chain_now, chain_now + 10**5, False],
                )  # fmt: skip
                await rpc("evm_mine", [])
                return "0x" + proof_id.hex(), block

            genesis = await rpc("eth_getBlockByNumber", ["0x0", False])
            deployed = await rpc("eth_getBlockByNumber", [hex(first_block), False])
            identity = {
                "chain_id": 31337,
                "genesis_block_hash": genesis["hash"].lower(),
                "deployment_block": first_block,
                "deployment_block_hash": deployed["hash"].lower(),
                "source_commit_sha": sha.strip(),
                "contracts": {
                    name: {
                        "address": address_,
                        "constructor_arguments": arguments,
                        "abi_sha256": hashlib.sha256(
                            (CONTRACTS / f"abi/{name}.json").read_bytes()
                        ).hexdigest(),
                    }
                    for name, address_, arguments in (
                        ("IssuerRegistry", issuers, [admin]),
                        ("IssuerKeyRegistry", keys, [admin, issuers]),
                        ("ProofStatusRegistry", proofs, [admin, gateway, issuers, keys]),
                    )
                },
            }
            legacy_manifest = tmp_path / "31337.legacy.json"
            legacy_manifest.write_text(json.dumps({
                **identity,
                "deployment_id": "dep_" + hashlib.sha256(
                    json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                "roles": {"registry_admin": admin, "issuer_manager": issuer_manager,
                          "key_manager": key_manager, "issuer_account": issuer_account,
                          "gateway": gateway},
            }))  # fmt: skip

            primary, fallback = Proxy(anvil_port), Proxy(anvil_port)
            proxies += [primary, fallback]
            await primary.start()
            await fallback.start()

            from originproof_api import main
            from originproof_api.settings import Settings

            async def no_cleanup(app, restart):
                return []

            async def no_maintenance(app, stop):
                await stop.wait()

            # 분석 정리·유지 작업만 끈다(그 테이블은 이 검사 범위 밖).
            # 지갑 연결·projection 은 실제 경로 그대로.
            monkeypatch.setattr(main, "cleanup", no_cleanup)
            monkeypatch.setattr(main, "maintenance", no_maintenance)
            settings = Settings(
                _env_file=None,
                chain_target="anvil",
                database_url=(
                    f"postgresql+asyncpg://originproof:originproof@127.0.0.1:{pg_port}/originproof"
                ),
                blockchain_rpc_url=f"http://127.0.0.1:{primary.port}",
                blockchain_rpc_fallback_url=f"http://127.0.0.1:{fallback.port}",
                wallet_registry_address=address,
                wallet_manifest_path=str(manifest_path),
                blockchain_manifest_path=str(legacy_manifest),
                projection_enabled=True,
                projection_poll_seconds=1,
            )
            app = main.create_app(settings=settings)
            reader = None

            def model_tuple(function, parameter, model):
                field = next(
                    x for x in reader.functions[function]["inputs"] if x["name"] == parameter
                )
                data = model.model_dump(by_alias=True)
                return tuple(
                    hex_bytes(data[x["name"]], 32)
                    if x["type"] == "bytes32"
                    else int(data[x["name"]])
                    if x["type"].startswith("uint")
                    else data[x["name"]]
                    for x in field["components"]
                )

            async def send(function, values, sender):
                args = named(reader.functions[function]["inputs"], values)
                tx_hash = await rpc(
                    "eth_sendTransaction",
                    [{"from": sender, "to": address, "gas": "0x800000",
                      "data": "0x" + calldata(reader, function, args).hex()}],
                )  # fmt: skip
                receipt = await mined(tx_hash)
                await rpc("evm_mine", [])  # one block on top: confirmed for the projection
                return int(receipt["blockNumber"], 16)

            async def journal_rows():
                async with app.state.database.engine.connect() as conn:
                    rows = await conn.execute(select(journal.c.block_number, journal.c.payload))
                    return {
                        (row.block_number, json.loads(row.payload)["decoded"]["name"])
                        for row in rows
                    }

            async def projected(block):
                for _ in range(300):
                    view = app.state.wallet_projection
                    if view.status == "SYNCED" and view.checkpoint_block >= block:
                        return await journal_rows()
                    await asyncio.sleep(0.1)
                pytest.fail(f"wallet projection did not reach {block}: {view}")

            async def legacy_projected(block):
                for _ in range(300):
                    view = app.state.projection
                    if view.status == "SYNCED" and (view.checkpoint_block or 0) >= block:
                        async with app.state.database.engine.connect() as conn:
                            rows = await conn.execute(
                                select(proof_events.c.block_number, proof_events.c.proof_id_hash,
                                       proof_events.c.event_type)
                            )  # fmt: skip
                            return {tuple(row) for row in rows}
                    await asyncio.sleep(0.1)
                pytest.fail(f"legacy projection did not reach {block}: {view}")

            # 기존 projection 표는 운영에서 alembic 이 만든다. 일회용 DB 에서는 같은 정의로 만든다.
            async with app.state.database.engine.begin() as conn:
                await conn.run_sync(legacy_metadata.create_all)

            async with app.router.lifespan_context(app):
                runtime = app.state.wallet_runtime
                failover = runtime.chain.rpc
                assert isinstance(failover, FailoverWalletRpc)
                assert runtime.connect.rpc_index == 0 and not failover.on_fallback
                reader = failover.endpoints[0]
                issuer = identifier_hash("synthetic-failover-live")
                assert await runtime.rpc("issuer", issuer) is None

                domain = WalletDomain(chain_id="31337", verifying_contract=address)
                now = int((await failover.snapshot())["timestamp"], 16)
                proposal = GovernanceProposal(
                    action=1, issuer_id=issuer, key_id=identifier_hash("failover-live-key"),
                    signer=institution, metadata_hash=identifier_hash("failover-live-metadata"),
                    nonce="0", deadline=now + 3600,
                )  # fmt: skip
                proof = KeyProofMessage(
                    application_id=identifier_hash("failover-live-application"),
                    issuer_id=issuer, signer=institution,
                    challenge_nonce=identifier_hash("failover-live-challenge"),
                    deadline=now + 3600,
                )  # fmt: skip
                signature = await rpc(
                    "eth_signTypedData_v4", [institution, json.dumps(typed_data(domain, proof))]
                )
                proposed = await send(
                    "propose",
                    [model_tuple("propose", "proposal", proposal),
                     model_tuple("propose", "proof", proof), hex_bytes(signature)],
                    approvers[0],
                )  # fmt: skip
                pid = hex_bytes(proposal_id(domain, proposal), 32)
                first = await send("approve", [pid], approvers[0])
                before = await projected(first)
                assert {block for block, _ in before} >= {proposed, first}
                # 같은 시점에 기존 ProofStatusRegistry 이벤트도 자기 표에 반영된다.
                proof_one, proof_one_block = await register_proof("failover-live-proof-1")
                legacy_before = await legacy_projected(proof_one_block)
                assert (proof_one_block, proof_one, "REGISTERED") in legacy_before
                assert primary.requests > 0 and fallback.requests == 0

                # 실행 중 주 RPC 단절: 열린 연결도 끊고 새 연결은 거부.
                await primary.stop()
                cut_requests = primary.requests
                second = await send("approve", [pid], approvers[1])
                found = await runtime.rpc("issuer", issuer)
                assert found is not None and found.state == "ACTIVE"
                assert failover.on_fallback and fallback.requests > 0
                after = await projected(second)
                names = {name for block, name in after if block == second}
                assert "ProposalApproved" in names and len(names) >= 2, names  # + execution
                # 주 단절 중에도 기존 projection 은 보조로 새 기존 이벤트를 반영한다.
                proof_two, proof_two_block = await register_proof("failover-live-proof-2")
                legacy_after = await legacy_projected(proof_two_block)
                assert (proof_two_block, proof_two, "REGISTERED") in legacy_after
                assert legacy_before <= legacy_after
                assert app.state.wallet_projection.status == "SYNCED"
                assert primary.requests == cut_requests

                # 보조 사용 시간이 지나면 다시 주 RPC 부터.
                await primary.start()
                failover.clock = lambda: time.monotonic() + failover.fallback_seconds + 1
                assert (await runtime.rpc("issuer", issuer)).state == "ACTIVE"
                assert primary.requests > cut_requests and not failover.on_fallback

            # 다른 체인 상태(배포 없는 Anvil)는 보조 검증을 통과하지 못한다.
            other = start_anvil(other_port)
            for _ in range(100):
                try:
                    await rpc("eth_chainId", [], f"http://127.0.0.1:{other_port}")
                    break
                except httpx.TransportError:
                    await asyncio.sleep(0.05)
            deployment, _ = load_wallet_deployment(manifest_path, chain_id=31337, address=address)
            refused = FailoverWalletRpc(
                client, ("http://127.0.0.1:1", f"http://127.0.0.1:{other_port}"), **deployment
            )
            with pytest.raises(DependencyUnavailableError):
                await refused.read("nextNonce", [hex_bytes(issuer, 32)])
            assert not refused.on_fallback
    finally:
        for proxy in proxies:
            if proxy.server is not None and proxy.server.is_serving():
                await proxy.stop()
        for process in (anvil, other):
            if process is not None:
                process.terminate()
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.kill()
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)
