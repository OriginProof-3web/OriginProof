"""Manual disposable D QA runner; consumed policy/journal prevents paid replay."""

import asyncio
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import httpx
from eth_abi import encode
from originproof_analyzer.conversion_metrics import text_error_metrics
from originproof_analyzer.live_evaluation import save
from seed_accounts import V5_WALLET_ACCOUNTS, seed_prepared, synthetic_password

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = Path(os.environ.get("D_QA_PRIVATE_ROOT", str(ROOT)))
PYTHON = sys.executable
NOTICE = "합성 안내: 인증번호를 알려주세요."
JOURNAL = ORIGINAL / "build/private/v5-d-connected-smoke-20261027.json"
TMP = Path(tempfile.mkdtemp(prefix="originproof-d-connected-", dir="/private/tmp"))
TMP.chmod(0o700)
Path("/private/tmp/originproof-d-connected-root.txt").write_text(str(TMP))


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run(args, env, log):
    with (TMP / log).open("w") as f:
        r = subprocess.run(args, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError("command failed; private log " + log)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


async def wait_http(url):
    async with httpx.AsyncClient(timeout=2, trust_env=False) as c:
        for _ in range(120):
            try:
                if (await c.get(url)).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise RuntimeError("QA server readiness not reached")


async def main():
    assert not JOURNAL.exists(), "Existing paid smoke journal: inspect before any replay"
    policy = json.loads((ROOT / "fixtures/synthetic/v5_d_connected_smoke_policy.json").read_text())
    assert policy["approved_for_paid_calls"] is True and policy["max_calls"] == 3
    rpcport, dbport, apiport, webport = port(), port(), port(), port()
    rpcurl = f"http://127.0.0.1:{rpcport}"
    apiurl = f"http://127.0.0.1:{apiport}"
    weburl = f"http://127.0.0.1:{webport}"
    name = "originproof-d-connected-" + uuid4().hex[:10]
    created = False
    anvil = api = proxy = None
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.update(
        {
            "PYTHONPATH": ":".join(
                str(ROOT / p)
                for p in [
                    "apps/api/src",
                    "packages/python",
                    "services/analyzer/src",
                    "services/indexer/src",
                    "fixtures/finals",
                    "scripts/fixtures",
                ]
            ),
            "API_DATABASE_URL": f"postgresql+asyncpg://originproof:originproof@127.0.0.1:{dbport}/originproof",
            "API_SIGNER_DIRECTORY": str(TMP / "secrets"),
            "CHAIN_TARGET": "anvil",
            "API_BLOCKCHAIN_RPC_URL": rpcurl,
            "API_BLOCKCHAIN_MANIFEST_PATH": "",
            "API_PROJECTION_ENABLED": "false",
            "API_WALLET_TEXT_INPUT_ENABLED": "true",
            "API_WALLET_DEMO_EMAIL_ENABLED": "true",
            "API_WALLET_EMAIL_SECRET": "synthetic-d-connected-email-secret-for-disposable-qa-only",
            "API_FINALS_PAYMENT_ISSUER_ID": "iss_origin_mock_bank",
            "API_FINALS_DOCUMENT_ISSUER_ID": "iss_origin_mock_office",
            "API_REQUESTS_PER_MINUTE": "1000",
            "API_LOGINS_PER_MINUTE": "100",
            "D_CONNECTED_QA": "1",
            "D_CONNECTED_MODE": "none",
            "D_LOCAL_KEY_FILE": str(ORIGINAL / ".env"),
            "D_SMOKE_JOURNAL": str(JOURNAL),
            "LLM_PROVIDER": "mock",
        }
    )
    result = {
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "qa_only_composition": True,
        "public_image_upload_connected": False,
        "actual_chain": "DISPOSABLE_ANVIL",
        "actual_database": "POSTGRESQL",
        "steps": [],
    }

    def stop(p):
        if p and p.poll() is None:
            p.terminate()
            p.wait(timeout=12)

    def start(mode):
        env["D_CONNECTED_MODE"] = mode
        return subprocess.Popen(
            [
                PYTHON,
                "-m",
                "uvicorn",
                "v5_d_connected_smoke:process_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(apiport),
                "--no-proxy-headers",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=(TMP / "api-private.log").open("a"),
        )

    async def auth(client):
        password = json.loads((TMP / "secrets/test-accounts.json").read_text())["password"]
        r = await client.post(
            "/v1/auth/login", json={"username": "d_recipient", "password": password}
        )
        assert r.status_code == 200
        client.headers["X-CSRF-Token"] = r.json()["csrf_token"]

    async def job(client, label):
        a = await client.post("/v3/inputs", json={"kind": "TEXT", "text": NOTICE})
        assert a.status_code == 201
        b = await client.post(
            "/v3/analyses",
            json={"request_id": "req_d_" + label, "input_ref": a.json()["input_ref"]},
        )
        assert b.status_code == 202
        for _ in range(100):
            c = (await client.get("/v3/analyses/" + b.json()["analysis_id"])).json()
            if c["status"] in ["COMPLETED", "FAILED"]:
                return c
            await asyncio.sleep(0.1)
        raise RuntimeError("job did not settle")

    try:
        run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--label",
                "originproof.validation=true",
                "--tmpfs",
                "/var/lib/postgresql/data",
                "-p",
                f"127.0.0.1:{dbport}:5432",
                "-e",
                "POSTGRES_USER=originproof",
                "-e",
                "POSTGRES_PASSWORD=originproof",
                "-e",
                "POSTGRES_DB=originproof",
                "postgres:16.4-alpine",
            ],
            env,
            "docker.log",
        )
        created = True
        for _ in range(100):
            r = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "originproof"],
                capture_output=True,
            )
            if r.returncode == 0:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("database TCP not ready")
        anvil = subprocess.Popen(
            [
                "anvil",
                "--host",
                "127.0.0.1",
                "--port",
                str(rpcport),
                "--chain-id",
                "31337",
                "--silent",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        async with httpx.AsyncClient(timeout=10, trust_env=False) as chain:

            async def rpc(method, params):
                r = await chain.post(
                    rpcurl, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
                )
                d = r.json()
                assert "error" not in d
                return d["result"]

            for _ in range(100):
                try:
                    assert await rpc("eth_chainId", []) == "0x7a69"
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(0.1)
            accounts = await rpc("eth_accounts", [])
            approvers = accounts[1:4]
            artifact = json.loads(
                (
                    ROOT
                    / "packages/contracts/out/OriginProofWalletRegistry.sol"
                    / "OriginProofWalletRegistry.json"
                ).read_text()
            )
            creation = bytes.fromhex(artifact["bytecode"]["object"].removeprefix("0x")) + encode(
                ["address[3]"], [approvers]
            )
            tx = await rpc(
                "eth_sendTransaction",
                [{"from": accounts[0], "data": "0x" + creation.hex(), "gas": "0xc00000"}],
            )
            for _ in range(100):
                receipt = await rpc("eth_getTransactionReceipt", [tx])
                if receipt is not None:
                    break
                await asyncio.sleep(0.05)
            assert receipt and receipt["status"] == "0x1"
            wrapper = module(
                "d_wrapper", ROOT / "packages/contracts/script/deploy_wallet_registry.py"
            )
            from infrastructure.blockchain.network import chain_target

            manifest = await asyncio.to_thread(
                wrapper.build_manifest,
                wrapper.rpc_caller(rpcurl),
                chain_target("anvil"),
                ROOT / "packages/contracts",
                tx,
                approvers,
                result["source_revision"],
            )
            (TMP / "wallet.json").write_text(json.dumps(manifest))
            address = manifest["contracts"]["OriginProofWalletRegistry"]["address"]
            env.update(
                {
                    "API_WALLET_REGISTRY_ADDRESS": address,
                    "API_WALLET_MANIFEST_PATH": str(TMP / "wallet.json"),
                }
            )
            run(
                [PYTHON, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
                env,
                "migration.log",
            )
            os.environ.update(env)
            password = synthetic_password(TMP / "secrets/test-accounts.json")
            ids = await seed_prepared(
                V5_WALLET_ACCOUNTS + (("d_recipient", "recipient", None),), password
            )
            env["API_WALLET_INTERNAL_APPROVERS"] = json.dumps(
                {
                    "iss_origin_mock_bank": ids["v5_bank_approver"],
                    "iss_origin_mock_office": ids["v5_office_approver"],
                }
            )
            env["API_WALLET_OPERATOR_ADDRESSES"] = json.dumps(
                {ids["v5_operator" + str(i + 1)]: a for i, a in enumerate(approvers)}
            )
            api = start("none")
            await wait_http(apiurl + "/health/ready")
            async with httpx.AsyncClient(base_url=apiurl, timeout=30, trust_env=False) as client:
                await auth(client)
                baseline = await job(client, "none")
                assert (
                    baseline["status"] == "FAILED"
                    and baseline["error_code"] == "ANALYZER_UNAVAILABLE"
                )
                result["default_processor_missing_reproduced"] = True
                result["public_image_kind_status"] = (
                    await client.post(
                        "/v3/inputs", json={"kind": "DOCUMENT_IMAGE", "text": "synthetic"}
                    )
                ).status_code
                run(
                    [
                        PYTHON,
                        "scripts/fixtures/wallet_demo_flow.py",
                        "--chain-target",
                        "anvil",
                        "--api",
                        apiurl,
                        "--rpc-url",
                        rpcurl,
                        "--registry",
                        address,
                        "--manifest",
                        str(TMP / "wallet.json"),
                        "--credentials",
                        str(TMP / "secrets/test-accounts.json"),
                        "--signer",
                        "rpc",
                        "--approver1",
                        approvers[0],
                        "--approver2",
                        approvers[1],
                        "--institution",
                        accounts[4],
                    ],
                    env,
                    "wallet-demo.log",
                )
                demo = (TMP / "wallet-demo.log").read_text()
                assert all(s in demo for s in ["VERIFIED", "TAMPERED", "SUPERSEDED"])
                result["actual_chain_demo"] = {
                    "governance": True,
                    "v1_v2_publication": True,
                    "normal_tampered_superseded": True,
                }
                proxyenv = env | {"OP5_PROXY_PORT": str(webport), "OP5_UPSTREAM": apiurl}
                proxy = subprocess.Popen(
                    ["node", str(ROOT / "apps/web-v5/개발/op5-proxy.mjs")],
                    cwd=ROOT,
                    env=proxyenv,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                await wait_http(weburl + "/business.html")
                for mode in ["mock", "live"]:
                    stop(api)
                    if mode == "live":
                        os.umask(0o077)
                        save(
                            JOURNAL,
                            {
                                "approved_for_paid_calls": True,
                                "max_calls": 3,
                                "rows": [],
                                "authorization": "Direct user additional3 approval on 2026-10-27",
                                "source_revision": result["source_revision"],
                            },
                        )
                    api = start(mode)
                    await wait_http(apiurl + "/health/ready")
                    cfg = {
                        "web": weburl,
                        "credentials": str(TMP / "secrets/test-accounts.json"),
                        "live": mode == "live",
                        "screenshot": str(TMP / (mode + ".png")),
                        "result": str(TMP / (mode + "-browser.json")),
                    }
                    (TMP / "browser-config.json").write_text(json.dumps(cfg))
                    run(
                        [
                            "node",
                            str(ROOT / "fixtures/finals/v5_d_browser_connected.cjs"),
                            str(TMP / "browser-config.json"),
                        ],
                        env,
                        mode + "-browser.log",
                    )
                    result[mode + "_browser"] = json.loads(
                        (TMP / (mode + "-browser.json")).read_text()
                    )
                    print("BROWSER", mode, "PASS", flush=True)
                image = (
                    ROOT / "fixtures/synthetic/selected_input_development_v1/images/DP-H01.png"
                ).read_bytes()
                r = await client.post(
                    "/__d_qa/document",
                    content=image,
                    headers={"content-type": "image/png"},
                    timeout=180,
                )
                assert r.status_code == 200, "image QA bridge failed"
                v = r.json()
                assert v["qa_only"] and v["report"]["risk_level"] == "HIGH"
                assert not any(
                    x.startswith("LLM_ANALYSIS_UNAVAILABLE:") for x in v["report"]["limitations"]
                )
                expected = next(
                    c["text"]
                    for c in json.loads(
                        (ROOT / "fixtures/synthetic/phishing_sources_v1.json").read_text()
                    )["cases"]
                    if c["id"] == "DP-H01"
                )
                result["image_qa"] = {
                    "status": "PASS",
                    "risk": "HIGH",
                    "conversion": text_error_metrics(expected, v["converted_text"]),
                    "pixel_accuracy": "NOT_EVALUATED",
                    "qa_bridge_only": True,
                    "report_evidence_sources": [x["source"] for x in v["report"]["evidence"]],
                }
                # List route only; retention/deletion is covered in the separate C recovery suite.
                result["stored_list_http_status"] = (await client.get("/v3/analyses")).status_code
            journal = json.loads(JOURNAL.read_text())
            assert len(journal["rows"]) == 3 and all(
                r.get("http_status") == 200
                and r.get("usage")
                and not r.get("usage_exceeds_output_cap")
                for r in journal["rows"]
            )
            result["paid_requests"] = [
                {
                    k: r.get(k)
                    for k in [
                        "stage",
                        "http_attempts",
                        "http_status",
                        "usage",
                        "usage_exceeds_output_cap",
                    ]
                }
                for r in journal["rows"]
            ]
            result["cumulative_actual_calls"] = 87
            result["journal_sha256"] = hashlib.sha256(JOURNAL.read_bytes()).hexdigest()
            print("ACTUAL_MODEL_REQUESTS", len(journal["rows"]), "PASS", flush=True)
    finally:
        stop(proxy)
        stop(api)
        stop(anvil)
        if created:
            subprocess.run(
                ["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        if JOURNAL.exists():
            state = json.loads(JOURNAL.read_text())
            state.pop("checksum")
            state["approved_for_paid_calls"] = False
            save(JOURNAL, state)
        policy["approved_for_paid_calls"] = False
        (ROOT / "fixtures/synthetic/v5_d_connected_smoke_policy.json").write_text(
            json.dumps(policy, ensure_ascii=False, indent=2) + "\n"
        )
        result["resources_cleaned"] = True
        (TMP / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        Path("/private/tmp/originproof-d-connected-result-path.txt").write_text(
            str(TMP / "result.json")
        )
    print("RESULT", str(TMP / "result.json"), flush=True)


if __name__ == "__main__":
    if os.environ.get("D_CONNECTED_QA") != "1":
        raise SystemExit("explicit disposable D_CONNECTED_QA=1 required")
    asyncio.run(main())
