"""Reuse frozen D #51 preparation against A's W2 web acceptance tests."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QA_SHA = "17f78e300b04aa9395fb20f6f76f5313d705db3d"
IMAGE = "originproof-w2-a-acceptance-deployer"
BUILD = ROOT / "build"


def main():
    if os.getenv("W2_BROWSER_QA") != "1":
        raise SystemExit("Set W2_BROWSER_QA=1 for a new disposable synthetic environment.")
    if (BUILD / "w2-browser-qa").exists():
        raise SystemExit("Preserve existing results; use a new clean checkout for another run.")
    subprocess.run(
        ["docker", "build", "-f", "infra/docker/deployer.Dockerfile", "-t", IMAGE, "."],
        cwd=ROOT,
        check=True,
    )
    sources = ("apps/api/src", "packages/python", "services/analyzer/src")
    os.environ["PYTHONPATH"] = os.pathsep.join(str(ROOT / source) for source in sources)
    for source in sources:
        sys.path.insert(0, str(ROOT / source))
    BUILD.mkdir(exist_ok=True)
    helper = BUILD / "w2-a-recovery-helper.py"
    runner = BUILD / "w2-a-browser-runner.py"
    for source, target in (
        ("scripts/ci/test_w2_recovery_qa.py", helper),
        ("fixtures/finals/prepare_w2_browser_qa.py", runner),
    ):
        code = subprocess.check_output(["git", "show", f"{QA_SHA}:{source}"], cwd=ROOT, text=True)
        code = code.replace(
            "Path(__file__).resolve().parents[2]", "Path(__file__).resolve().parents[1]"
        )
        code = code.replace("originproof-w2-recovery-deployer", IMAGE)
        code = code.replace(
            'ROOT / "scripts/ci/test_w2_recovery_qa.py"', 'ROOT / "build/w2-a-recovery-helper.py"'
        )
        code = code.replace(
            "../../fixtures/finals/w2_browser_qa.config.ts", "playwright.w2-live.config.ts"
        )
        if target == runner:
            code = code.replace(
                'and all(row.request_id.startswith("req_w2_prepare_") for row in operations)',
                'and statuses.get("iss_w2_approved") == "ACTIVE"\n'
                "                and len(operations) == 6\n"
                "                and sorted(\n"
                "                    (row.action, row.status) for row in operations\n"
                '                    if not row.request_id.startswith("req_w2_prepare_")\n'
                '                ) == [("register_issuer", "CONFIRMED"),\n'
                '                      ("register_key", "CONFIRMED"), ("revoke_key", "CONFIRMED")]',
            )
            code = code.replace(
                '"operation_count": len(operations),',
                '"operation_count": len(operations),\n'
                '                "browser_operations": [\n'
                '                    {"action": row.action, "status": row.status}\n'
                "                    for row in operations\n"
                '                    if not row.request_id.startswith("req_w2_prepare_")\n'
                "                ],",
            )
        target.write_text(code)
        target.chmod(0o600)
    environment = ROOT / ".env"
    created_environment = not environment.exists()
    if created_environment:
        environment.write_text("LLM_PROVIDER=mock\nOPENAI_MODEL=gpt-6-luna\n")
        environment.chmod(0o600)
    try:
        spec = importlib.util.spec_from_file_location("w2_a_runner", runner)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.main()
    finally:
        if created_environment:
            environment.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
