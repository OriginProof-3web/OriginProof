"""Start only the isolated synthetic web/API/DB/EVM environment; never reset existing data."""

import gzip
import json
import os
import secrets
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(
    os.environ.get("ORIGINPROOF_CONSOLE_ROOT", Path(__file__).resolve().parents[1] / "official")
)
STATE = Path.home() / ".local/share/originproof-admin-test"
SOURCE = Path("/tmp/originproof-admin-3ef1fd4")
SHA = "3ef1fd40943914c1450e8bc05047119ab7eabbc0"
DB = "postgresql+asyncpg://originproof:originproof@127.0.0.1:55434/originproof"
RPC = "http://127.0.0.1:18546"
CHILDREN = []


def run(args, **kw):
    return subprocess.run(args, check=True, **kw)


def alive(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def rpc(method, params):
    request = urllib.request.Request(
        RPC,
        json.dumps(dict(jsonrpc="2.0", id=1, method=method, params=params)).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        data = json.load(response)
    if "error" in data:
        raise RuntimeError("Local EVM state request failed")
    return data["result"]


def archive(repo, ref, destination):
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "source.tar.gz"
        with target.open("wb") as stream:
            run(["gh", "api", f"repos/{repo}/tarball/{ref}"], stdout=stream)
        with tarfile.open(target) as bundle:
            bundle.extractall(temporary, filter="data")
        next(p for p in Path(temporary).iterdir() if p.is_dir()).rename(destination)


def prepare():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not SOURCE.exists():
        archive("OriginProof-3web/OriginProof", SHA, SOURCE)
    for folder, repo, version in [
        ("openzeppelin-contracts", "OpenZeppelin/openzeppelin-contracts", "v5.7.0"),
        ("forge-std", "foundry-rs/forge-std", "v1.16.2"),
    ]:
        path = SOURCE / "packages/contracts/lib" / folder
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            archive(repo, version, path)
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("API_", "TEST_", "OPENAI_", "SEED_DATABASE_"))
    }
    env.update(
        PYTHONPATH="apps/api/src:packages/python:services/analyzer/src:services/indexer/src",
        UV_PROJECT_ENVIRONMENT=".uv-venv",
        API_DATABASE_URL=DB,
        API_BLOCKCHAIN_RPC_URL=RPC,
        API_BLOCKCHAIN_MANIFEST_PATH=str(
            SOURCE / "packages/contracts/deployments/31337.local.json"
        ),
        API_SIGNER_DIRECTORY=str(STATE / "signers"),
        LLM_PROVIDER="mock",
        API_PROJECTION_ENABLED="true",
        API_PROJECTION_POLL_SECONDS="1",
    )
    run(["uv", "sync", "--frozen", "--all-packages", "--all-groups"], cwd=SOURCE, env=env)
    if subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode:
        run(["colima", "start", "--cpu", "2", "--memory", "4"])
    existing = (
        subprocess.run(
            ["docker", "inspect", "originproof-admin-test-postgres"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    if existing:
        run(["docker", "start", "originproof-admin-test-postgres"], stdout=subprocess.DEVNULL)
    else:
        run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                "originproof-admin-test-postgres",
                "--label",
                "originproof-admin-test=1",
                "-e",
                "POSTGRES_DB=originproof",
                "-e",
                "POSTGRES_USER=originproof",
                "-e",
                "POSTGRES_PASSWORD=originproof",
                "-p",
                "127.0.0.1:55434:5432",
                "postgres:16.4-alpine",
            ],
            stdout=subprocess.DEVNULL,
        )
    for _ in range(50):
        if (
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "originproof-admin-test-postgres",
                    "pg_isready",
                    "-U",
                    "originproof",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        ):
            break
        time.sleep(0.2)
    try:
        rpc("eth_chainId", [])
    except OSError:
        native_state = STATE / "anvil-current-state.json"
        if not native_state.exists():
            native_state = STATE / "anvil-state.json"
        native_state_exists = native_state.exists()
        CHILDREN.append(
            subprocess.Popen(
                [
                    "anvil",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "18546",
                    "--chain-id",
                    "31337",
                    "--silent",
                    "--preserve-historical-states",
                    "--no-request-size-limit",
                    *(["--load-state", str(native_state)] if native_state_exists else []),
                ]
            )
        )
        for _ in range(50):
            try:
                rpc("eth_chainId", [])
                break
            except OSError:
                time.sleep(0.2)
        saved = STATE / "anvil-rpc-state.json"
        if saved.exists() and not native_state_exists:
            rpc("anvil_loadState", [json.loads(saved.read_text())])
    latest = rpc("eth_getBlockByNumber", ["latest", False])
    if int(latest["timestamp"], 16) < int(time.time()):
        rpc("evm_setNextBlockTimestamp", [int(time.time())])
        rpc("evm_mine", [])
    # Automine writes; avoid unbounded empty-block historical snapshots during idle use.
    rpc("evm_setIntervalMining", [0])
    rpc("evm_setAutomine", [True])
    manifest = SOURCE / "packages/contracts/deployments/31337.local.json"
    saved_manifest = STATE / "deployment-manifest.json"
    if not manifest.exists() and saved_manifest.exists():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(saved_manifest, manifest)
    if not manifest.exists():
        # Existing deploy script seeds Bank, which would bypass/fail the onboarding test.
        # Deploy the same contracts/roles without its demo seed, then restore archived source.
        script = SOURCE / "packages/contracts/script/DeployLocal.s.sol"
        original = script.read_text()
        try:
            script.write_text(original[: original.index("        bytes32 issuerId")] + "    }\n}\n")
            run(
                [
                    "uv",
                    "run",
                    "python",
                    "packages/contracts/script/deploy_local.py",
                    "--rpc-url",
                    RPC,
                    "--signer",
                    "0x1111111111111111111111111111111111111111",
                    "--source-commit-sha",
                    SHA,
                ],
                cwd=SOURCE,
                env=env,
            )
        finally:
            script.write_text(original)
    shutil.copyfile(manifest, saved_manifest)
    saved_manifest.chmod(0o600)
    run(
        ["uv", "run", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
        cwd=SOURCE,
        env=env,
    )
    accounts = STATE / "accounts.json"
    if not accounts.exists():
        data = [
            dict(username=n, role=r, issuer_id=i, password=secrets.token_urlsafe(18))
            for n, r, i in [
                ("bank", "issuer", "iss_origin_mock_bank"),
                ("office", "issuer", "iss_origin_mock_office"),
                ("recipient", "recipient", None),
                ("other-recipient", "recipient", None),
                ("operator", "operator", None),
            ]
        ]
        accounts.write_text(json.dumps(data))
        accounts.chmod(0o600)
    # Keep the existing website's synthetic login credentials and account IDs.
    website_accounts = Path.home() / ".local/share/originproof-web-test/accounts.json"
    if website_accounts.exists():
        accounts.write_text(website_accounts.read_text())
        accounts.chmod(0o600)
    seed = STATE / "seed.py"
    seed.write_text("""import asyncio,json,sys
from sqlalchemy import select
from originproof_api.database import Database,AccountRow
from originproof_api.accounts import password_hash
from originproof_api.settings import Settings
async def main():
 db=Database(Settings().database_url)
 async with db.session_factory() as session:
  for a in json.load(open(sys.argv[1])):
   row=await session.scalar(select(AccountRow).where(AccountRow.username==a['username']))
   if row:
    if row.role!=a['role'] or row.issuer_id!=a['issuer_id']:
     raise RuntimeError('Synthetic account identity mismatch')
    row.password_hash=password_hash(a['password'])
   else:
    session.add(AccountRow(account_id='acct_web_'+a['username'].replace('-','_'),username=a['username'],role=a['role'],issuer_id=a['issuer_id'],password_hash=password_hash(a['password'])))
  await session.commit()
 await db.dispose()
asyncio.run(main())
""")
    seed.chmod(0o600)
    run(["uv", "run", "python", str(seed), str(accounts)], cwd=SOURCE, env=env)
    if not alive("http://127.0.0.1:8780/health/live"):
        CHILDREN.append(
            subprocess.Popen(
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "originproof_api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8780",
                    "--no-access-log",
                ],
                cwd=SOURCE,
                env=env,
            )
        )
    if not alive("http://127.0.0.1:8781/health/live"):
        CHILDREN.append(
            subprocess.Popen(
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "originproof_analyzer.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8781",
                    "--no-access-log",
                ],
                cwd=SOURCE,
                env=env,
            )
        )
    for _ in range(100):
        if alive("http://127.0.0.1:8780/health/ready"):
            return
        time.sleep(0.2)
    raise RuntimeError("Local API startup failed")


def checkpoint():
    try:
        target = STATE / "anvil-rpc-state.json"
        temporary = target.with_suffix(".tmp")
        snapshot = rpc("anvil_dumpState", [False])
        # Persist current storage, block identities and receipts atomically. Saving every
        # historical storage snapshot blocked RPC for >5s and grew to hundreds of MB.
        native = gzip.decompress(bytes.fromhex(snapshot.removeprefix("0x")))
        json.loads(native)
        temporary.write_text(json.dumps(snapshot))
        temporary.chmod(0o600)
        temporary.replace(target)
        target = STATE / "anvil-current-state.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(native)
        temporary.chmod(0o600)
        temporary.replace(target)
    except OSError:
        pass


def shutdown(_signal, _frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    prepared = False
    try:
        os.umask(0o077)
        prepare()
        prepared = True
        checkpoint()
        while True:
            time.sleep(60)
            checkpoint()
    except KeyboardInterrupt:
        pass
    finally:
        if prepared:
            checkpoint()
        for process in reversed(CHILDREN):
            process.terminate()
        for process in reversed(CHILDREN):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
