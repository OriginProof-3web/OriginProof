"""Test-only TCP mode for wallet_api_probe; never an operational app factory."""

import asyncio
import json
import os
import socket
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import httpx
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_creation import WalletCreationProof
from infrastructure.blockchain.wallet_rpc import hex_bytes
from originproof_api.database import Database
from originproof_api.main import create_app
from originproof_api.settings import Settings
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]


def process_app():
    if not all(
        os.environ.get(flag) == "1"
        for flag in (
            "ORIGINPROOF_WALLET_LIVE",
            "ORIGINPROOF_WALLET_API_LIVE",
            "ORIGINPROOF_WALLET_API_PROCESS",
        )
    ):
        raise RuntimeError("disposable wallet process opt-in is required")
    config_path = Path(os.environ["ORIGINPROOF_WALLET_PROCESS_CONFIG"])
    config = json.loads(config_path.read_text())
    settings = Settings(_env_file=None, **config["settings"])
    url = make_url(settings.database_url)
    if (
        url.host != "127.0.0.1"
        or not (url.database or "").startswith("originproof_wallet_api_")
        or urlparse(config["rpc_url"]).hostname != "127.0.0.1"
        or config["deployment"]["chain_id"] != 31337
    ):
        raise RuntimeError("only disposable loopback DB and Anvil are allowed")
    database = Database(settings.database_url)
    app = create_app(database=database, settings=settings)
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        client = httpx.AsyncClient(timeout=5, trust_env=False)
        completed = False
        try:
            app.state.wallet_runtime.chain = await WalletRegistryReadAdapter.from_deployment(
                client,
                config["rpc_url"],
                creation_proof=WalletCreationProof(
                    config["creation_tx"],
                    hex_bytes(config["creation_bytecode"]),
                ),
                **config["deployment"],
            )
            async with original_lifespan(app):
                yield
            completed = True
        finally:
            await database.dispose()
            await client.aclose()
            config_path.with_name("lifespan.json").write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "lifespan_exited": completed,
                        "rpc_client_closed": client.is_closed,
                    }
                )
            )

    app.router.lifespan_context = lifespan
    return app


class ApiProcess:
    def __init__(self, directory, config):
        self.directory = Path(directory)
        self.config_path = self.directory / "config.json"
        self.state_path = self.directory / "lifespan.json"
        self.config_path.write_text(json.dumps(config))
        self.config_path.chmod(0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.process = None
        self.lifecycle = {}

    def client(self):
        return httpx.AsyncClient(base_url=self.url, timeout=10, trust_env=False)

    async def start(self):
        assert self.process is None or self.process.poll() is not None
        self.state_path.unlink(missing_ok=True)
        env = os.environ | {
            "ORIGINPROOF_WALLET_PROCESS_CONFIG": str(self.config_path),
            "PYTHONPATH": ":".join(
                str(ROOT / p)
                for p in (
                    "apps/api/src",
                    "packages/python",
                    "services/indexer/src",
                    "services/analyzer/src",
                    "services/indexer/tests",
                )
            ),
        }
        with (self.directory / "server.log").open("ab") as log:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "wallet_api_process:process_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                    "--lifespan",
                    "on",
                    "--no-proxy-headers",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        async with self.client() as client:
            for _ in range(100):
                assert self.process.poll() is None, "disposable API exited; see server.log"
                try:
                    live = await client.get("/health/live")
                    ready = await client.get("/health/ready")
                    if live.status_code == ready.status_code == 200:
                        return
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.1)
        raise AssertionError("disposable API did not become ready; see server.log")

    async def stop(self, *, kill=False):
        if self.process is not None and self.process.poll() is None:
            self.process.kill() if kill else self.process.terminate()
            try:
                await asyncio.to_thread(self.process.wait, 10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                await asyncio.to_thread(self.process.wait, 5)
                raise AssertionError(
                    "disposable API did not stop within the shutdown budget"
                ) from None


@asynccontextmanager
async def api_process(database, settings, reader, proof, abi):
    if os.environ.get("ORIGINPROOF_WALLET_API_PROCESS") != "1":
        yield None
        return
    with TemporaryDirectory(prefix="originproof-api-process-") as directory:
        server = ApiProcess(
            directory,
            {
                "settings": settings.model_dump(mode="json")
                | {
                    "database_url": database.engine.url.render_as_string(hide_password=False),
                },
                "rpc_url": reader.url,
                "deployment": {
                    "chain_id": reader.chain_id,
                    "address": reader.address,
                    "deployment_block": reader.deployment_block,
                    "deployment_hash": reader.deployment_hash,
                    "runtime_code_hash": reader.runtime_code_hash,
                    "abi": abi,
                },
                "creation_tx": proof.tx_hash,
                "creation_bytecode": "0x" + proof.creation_bytecode.hex(),
            },
        )
        try:
            await server.start()
            yield server
        finally:
            await server.stop()
        state = json.loads(server.state_path.read_text())
        assert state == {
            "pid": server.process.pid,
            "lifespan_exited": True,
            "rpc_client_closed": True,
        }
        server.lifecycle["graceful_shutdown"] = state
