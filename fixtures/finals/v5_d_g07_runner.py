"""Plan by default; explicitly opt in to fresh + mixed G07 QA on a merged, immutable candidate."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
G07_FIX_SHA = "61703197399a2f66f18a3e0fcae51fd2bf54131f"
REQUIRED_GROUPS = {
    "two_types_comparison",
    "mutation_permission_matrix",
    "unregistered",
    "ownership",
    "operation_audit_reconciliation",
    "suspended_new_issuance",
    "rpc_outage_recovery",
    "same_operation_recovery",
    "private_fields",
    "approval_chain_boundary",
    "default_request_limit",
    "default_login_limit",
    "origin_body_boundaries",
    "different_rpc_chain",
    "same_chain_fresh_rpc_guard",
    "projection_replay_process_restart_reorg",
    "current_candidate_lifecycle_regression",
    "legacy_v1_expiry",
}


def git_environment() -> dict[str, str]:
    """Make cwd select the QA repository even when invoked from a Git hook."""
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, env=git_environment(), capture_output=True)
    if result.returncode:
        raise ValueError("GIT_OBJECT_OR_REF_UNAVAILABLE")
    return result.stdout


def ancestor(root: Path, older: str, newer: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=root,
            env=git_environment(),
            capture_output=True,
        ).returncode
        == 0
    )


def preflight(product_sha: str, *, root: Path = ROOT, fix_sha: str = G07_FIX_SHA) -> dict:
    plan = {
        "status": "BLOCKED",
        "product_sha": product_sha,
        "required_fix_sha": fix_sha,
        "reasons": [],
        "live_executed": False,
    }
    if not re.fullmatch(r"[0-9a-f]{40}", product_sha):
        plan["reasons"].append("FULL_IMMUTABLE_COMMIT_SHA_REQUIRED")
        return plan
    try:
        if (
            git(root, "rev-parse", "--verify", product_sha + "^{commit}").decode().strip()
            != product_sha
        ):
            raise ValueError("FULL_IMMUTABLE_COMMIT_SHA_REQUIRED")
        phase = git(root, "rev-parse", "--verify", "origin/phase/W5^{commit}").decode().strip()
        plan["phase_sha"] = phase
        plan["qa_git_head"] = git(root, "rev-parse", "HEAD").decode().strip()
        if not ancestor(root, fix_sha, phase):
            plan["reasons"].append("G07_FIX_NOT_MERGED_IN_PHASE")
        if not ancestor(root, phase, product_sha):
            plan["reasons"].append("CANDIDATE_MUST_INCLUDE_CURRENT_PHASE")
        if git(root, "status", "--porcelain"):
            plan["reasons"].append("QA_WORKTREE_MUST_BE_CLEAN")
        lock = git(root, "show", product_sha + ":uv.lock")
        plan["lock_sha256"] = hashlib.sha256(lock).hexdigest()
        if lock != (root / "uv.lock").read_bytes():
            plan["reasons"].append("CANDIDATE_AND_QA_LOCKFILES_DIFFER")
    except (ValueError, OSError):
        plan["reasons"].append("GIT_OBJECT_REF_OR_LOCK_UNAVAILABLE")
    if not plan["reasons"]:
        plan["status"] = "READY_TO_EXECUTE_NOT_TESTED"
    return plan


def check_summary(summary: dict, plan: dict, mode: str) -> bool:
    """No green subsets, retries hiding failures, wrong products or unclosed resources."""
    rows = summary.get("results", [])
    environment = summary.get("environment", {})
    return (
        summary.get("verification_scope") == "MERGED_G07_CANDIDATE"
        and summary.get("product_sha") == plan["product_sha"]
        and summary.get("qa_git_head") == plan["qa_git_head"]
        and summary.get("qa_git_dirty") is False
        and summary.get("lifecycle_fixture_mode") == mode
        and summary.get("resources_closed") is True
        and not any(k in summary for k in ("setup_error_type", "cleanup_error_type"))
        and len(rows) == len(REQUIRED_GROUPS)
        and {row.get("id") for row in rows} == REQUIRED_GROUPS
        and all(row.get("status") == "PASS" for row in rows)
        and environment.get("paid_calls") == 0
        and environment.get("llm_provider") == "mock"
        and environment.get("source_config_sha256", {}).get("uv.lock") == plan["lock_sha256"]
    )


def private_report(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x", encoding="utf-8") as stream:
        path.chmod(0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def run_once(root: Path, plan: dict, mode: str, directory: Path) -> dict:
    directory.mkdir(mode=0o700)
    env = dict(
        git_environment(),
        W5_D_API_QA="1",
        W5_D_PRODUCT_SHA=plan["product_sha"],
        W5_D_OUTPUT_ROOT=str(directory),
        LLM_PROVIDER="mock",
        OPENAI_MODEL="gpt-6-luna",
    )
    env.pop("OPENAI_API_KEY", None)
    env.pop("W5_D_MIXED_STACK_QA", None)
    if mode == "MIXED_DIAGNOSTIC":
        env["W5_D_MIXED_STACK_QA"] = "1"
    with (directory / "runner.log").open("x") as log:
        (directory / "runner.log").chmod(0o600)
        result = subprocess.run(
            [
                "uv",
                "run",
                "--all-packages",
                "--all-groups",
                "--locked",
                "python",
                "fixtures/finals/w5_p0_api_qa.py",
            ],
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    reports = list(directory.glob("*/summary.json"))
    valid = False
    if len(reports) == 1:
        try:
            valid = check_summary(json.loads(reports[0].read_text()), plan, mode)
        except (ValueError, TypeError, AttributeError):
            pass
    return {
        "mode": mode,
        "status": "PASS" if result.returncode == 0 and valid else "FAIL",
        "exit_code": result.returncode,
        "report": str(reports[0]) if len(reports) == 1 else None,
    }


def execute(plan: dict, *, root: Path = ROOT, mixed_runs: int = 3) -> dict:
    if plan["status"] != "READY_TO_EXECUTE_NOT_TESTED" or not 3 <= mixed_runs <= 20:
        raise ValueError("ready preflight and 3..20 mixed runs required")
    out = root / "build/w5-d-g07" / uuid4().hex
    out.mkdir(parents=True, mode=0o700)
    result = dict(plan, status="FAIL", live_executed=False, runs=[])
    modes = ["FRESH"] + ["MIXED_DIAGNOSTIC"] * mixed_runs
    for index, mode in enumerate(modes):
        current = preflight(plan["product_sha"], root=root)
        if current != plan:
            result["blocked_reason"] = "PREFLIGHT_CHANGED_DURING_RUN"
            break
        result["live_executed"] = True
        try:
            row = run_once(root, plan, mode, out / f"{index + 1:02d}-{mode.lower()}")
        except Exception:
            row = {"mode": mode, "status": "FAIL", "reason": "RUNNER_FAILED_SEE_PRIVATE_LOG"}
        result["runs"].append(row)
        if mode == "FRESH" and row["status"] != "PASS":
            break
    if len(result["runs"]) == len(modes) and all(r["status"] == "PASS" for r in result["runs"]):
        result["status"] = "PASS_REQUIRES_B_C_REVIEW"
    private_report(out / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-sha", required=True)
    parser.add_argument("--execute", action="store_true", help="create owned disposable resources")
    parser.add_argument("--mixed-runs", type=int, choices=range(3, 21), default=3)
    args = parser.parse_args()
    plan = preflight(args.product_sha)
    if args.execute and plan["status"] == "READY_TO_EXECUTE_NOT_TESTED":
        plan = execute(plan, mixed_runs=args.mixed_runs)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 2 if plan["status"] == "BLOCKED" else 1 if plan["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
