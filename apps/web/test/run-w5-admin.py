"""A reexecution: existing 8768 UI, frozen C API, D's owned disposable fixture.

Only accounts are seeded. Applications, approvals, keys and proofs are created
through the browser. This is not D's independent browser acceptance or review.
"""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
C_SHA = "3ef1fd40943914c1450e8bc05047119ab7eabbc0"
D_SHA = "a3f55c6991061ac445d2223f19ff1b2a48acab0e"


def main():
    if os.getenv("W5_ADMIN_QA") != "1":
        raise SystemExit("Set W5_ADMIN_QA=1 to create a disposable synthetic stack.")
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ.pop("OPENAI_API_KEY", None)
    out = Path(os.getenv("W5_ADMIN_OUTPUT_DIR", str(ROOT / "build" / "w5-admin"))) / uuid4().hex
    out.mkdir(parents=True, mode=0o700)
    source = out / "d-qa.py"
    source.write_bytes(subprocess.check_output(
        ["git", "show", f"{D_SHA}:fixtures/finals/w5_p0_api_qa.py"], cwd=ROOT))
    spec = importlib.util.spec_from_file_location("w5_d_fixture", source)
    qa = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = qa
    spec.loader.exec_module(qa)
    original_command = qa.command
    qa.command = lambda args, cwd=ROOT, timeout=240: original_command(args, cwd=cwd, timeout=timeout)
    # D compares the product lock to the selected product baseline, not A's UI
    # branch lock. Keep that immutable baseline explicit instead of skipping it.
    baseline = out / "baseline"
    baseline.mkdir()
    (baseline / "uv.lock").write_bytes(subprocess.check_output(
        ["git", "show", f"{C_SHA}:uv.lock"], cwd=ROOT))
    qa.ROOT = baseline
    qa.PRODUCT_SHA = C_SHA
    qa.DEPLOYER = "originproof-w5-a-admin-deployer:3ef1fd4"
    _, helper, _, sources = qa.materialize(out)
    resources = helper.disposable_stack.__wrapped__(out)
    env = next(resources)
    try:
        if not Path(env["manifest"]).is_file():
            raise RuntimeError("Deployment manifest missing: use W5_ADMIN_OUTPUT_DIR under a Docker-shared directory.")
        from originproof_api.accounts import password_hash
        from originproof_api.database import AccountRow, Database
        from originproof_api.settings import Settings
        settings = Settings(_env_file=None, database_url=env["database_url"],
            blockchain_rpc_url=env["rpc_url"], blockchain_manifest_path=env["manifest"],
            signer_directory=str(out / "signers"),
            finals_payment_issuer_id="iss_w5_bank_" + out.name[:8],
            finals_document_issuer_id="iss_w5_office_" + out.name[:8],
            requests_per_minute=1000,
            logins_per_minute=100, browser_origins=["http://127.0.0.1:8768"])
        accounts = [{"username": role, "password": secrets.token_urlsafe(24),
            "account_id": "acct_w5_" + role.replace('-', '_'),
            "role": "issuer" if role in ("bank", "office") else
                    "operator" if role == "operator" else "recipient",
            "issuer_id": settings.finals_payment_issuer_id if role == "bank" else
                         settings.finals_document_issuer_id if role == "office" else None}
            for role in ("operator", "bank", "office", "recipient", "other-recipient")]
        async def seed_accounts():
            db = Database(settings.database_url)
            try:
                async with db.session_factory() as session:
                    session.add_all([AccountRow(**{k:v for k,v in a.items() if k != "password"},
                        password_hash=password_hash(a["password"])) for a in accounts])
                    await session.commit()
            finally:
                await db.dispose()
        asyncio.run(seed_accounts())
        account_file = out / "accounts.json"
        qa.private_json(account_file, accounts)
        with qa.server(settings) as (url, _):
            metadata = out / "environment.json"
            qa.private_json(metadata, {"api": url, "accounts": str(account_file),
                "c_sha": C_SHA, "d_fixture_sha": D_SHA, "sources": sources,
                "seed": "accounts only", "functional_request_budget": 1000,
                "independent_d_acceptance": False})
            result = subprocess.run([str(ROOT / "apps/web/node_modules/.bin/playwright"),
                "test", "e2e/w5-admin-live.spec.ts", "--workers=1"], cwd=ROOT / "apps/web",
                env=os.environ | {"ORIGINPROOF_WEB_BASE_URL":"http://127.0.0.1:8768",
                                  "W5_ADMIN_ENV":str(metadata)})
            qa.private_json(out / "result.json", {"exit_code":result.returncode,
                "c_sha":C_SHA,"d_fixture_sha":D_SHA,"ui":"http://127.0.0.1:8768/admin.html",
                "role_forwarding":"browser requests forwarded to real isolated API",
                "seed":"accounts only","independent_d_acceptance":False})
            print("W5 administrator evidence:", out / "result.json", flush=True)
            return result.returncode
    finally:
        resources.close()


if __name__ == "__main__":
    raise SystemExit(main())
