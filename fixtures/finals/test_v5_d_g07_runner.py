"""No Docker/network: real temporary Git histories and simulated QA reports test G07 gates."""

import hashlib
import json
import subprocess

import pytest
import v5_d_g07_runner as runner


def git(root, *args):
    return (
        subprocess.check_output(
            ["git", *args], cwd=root, env=runner.git_environment(), stderr=subprocess.DEVNULL
        )
        .decode()
        .strip()
    )


def commit(root, message):
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=QA fixture",
        "-c",
        "user.email=qa@example.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path):
    git(tmp_path, "init", "--quiet")
    (tmp_path / "uv.lock").write_text("version = 1\n")
    old = commit(tmp_path, "synthetic baseline")
    (tmp_path / "fix.txt").write_text("synthetic G07 fix\n")
    fixed = commit(tmp_path, "synthetic fix")
    git(tmp_path, "update-ref", "refs/remotes/origin/phase/W5", fixed)
    return tmp_path, old, fixed


def test_clean_candidate_includes_merged_fix_and_identical_lock(history):
    root, _, fixed = history
    plan = runner.preflight(fixed, root=root, fix_sha=fixed)
    assert plan["status"] == "READY_TO_EXECUTE_NOT_TESTED"
    assert plan["live_executed"] is False
    assert plan["lock_sha256"] == hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()


def test_parent_git_environment_cannot_redirect_qa_reads_or_fixture_writes(
    history, tmp_path_factory, monkeypatch
):
    root, _, fixed = history
    other = tmp_path_factory.mktemp("other-repository")
    git(other, "init", "--quiet")
    (other / "preserved.txt").write_text("must stay unchanged")
    preserved = commit(other, "unrelated repository")
    index = (other / ".git/index").read_bytes()
    for key, value in {
        "GIT_DIR": str(other / ".git"),
        "GIT_WORK_TREE": str(other),
        "GIT_COMMON_DIR": str(other / ".git"),
        "GIT_INDEX_FILE": str(other / ".git/index"),
        "GIT_OBJECT_DIRECTORY": str(other / ".git/objects"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.bare",
        "GIT_CONFIG_VALUE_0": "true",
    }.items():
        monkeypatch.setenv(key, value)
    plan = runner.preflight(fixed, root=root, fix_sha=fixed)
    assert plan["status"] == "READY_TO_EXECUTE_NOT_TESTED"
    (root / "fix.txt").write_text("another synthetic fix\n")
    changed = commit(root, "isolated fixture commit")
    assert runner.git(root, "rev-parse", "HEAD").decode().strip() == changed != fixed
    assert runner.ancestor(root, fixed, changed)
    assert git(other, "rev-parse", "HEAD") == preserved
    assert (other / ".git/index").read_bytes() == index
    assert (other / "preserved.txt").read_text() == "must stay unchanged"


@pytest.mark.parametrize("sha", ["HEAD", "origin/phase/W5", "--all", "abc1234", "f" * 40])
def test_moving_missing_or_non_commit_references_never_provision(history, sha):
    root, _, fixed = history
    assert runner.preflight(sha, root=root, fix_sha=fixed)["status"] == "BLOCKED"


@pytest.mark.parametrize(
    "fault", ["unmerged", "old_candidate", "dirty", "different_lock", "missing_ref"]
)
def test_each_candidate_precondition_fails_closed(history, fault):
    root, old, fixed = history
    candidate = fixed
    expected = {
        "unmerged": "G07_FIX_NOT_MERGED_IN_PHASE",
        "old_candidate": "CANDIDATE_MUST_INCLUDE_CURRENT_PHASE",
        "dirty": "QA_WORKTREE_MUST_BE_CLEAN",
        "different_lock": "CANDIDATE_AND_QA_LOCKFILES_DIFFER",
        "missing_ref": "GIT_OBJECT_REF_OR_LOCK_UNAVAILABLE",
    }[fault]
    if fault == "unmerged":
        git(root, "update-ref", "refs/remotes/origin/phase/W5", old)
    elif fault == "old_candidate":
        candidate = old
    elif fault == "dirty":
        (root / "unreviewed.txt").write_text("uncommitted")
    elif fault == "different_lock":
        (root / "uv.lock").write_text("version = 2\n")
        commit(root, "synthetic QA lock differs from candidate")
    else:
        git(root, "update-ref", "-d", "refs/remotes/origin/phase/W5")
    plan = runner.preflight(candidate, root=root, fix_sha=fixed)
    assert plan["status"] == "BLOCKED" and expected in plan["reasons"]


def good_summary(plan, mode="MIXED_DIAGNOSTIC"):
    return {
        "verification_scope": "MERGED_G07_CANDIDATE",
        "product_sha": plan["product_sha"],
        "qa_git_head": plan["qa_git_head"],
        "qa_git_dirty": False,
        "lifecycle_fixture_mode": mode,
        "resources_closed": True,
        "environment": {
            "paid_calls": 0,
            "llm_provider": "mock",
            "source_config_sha256": {"uv.lock": plan["lock_sha256"]},
        },
        "results": [{"id": name, "status": "PASS"} for name in sorted(runner.REQUIRED_GROUPS)],
    }


@pytest.mark.parametrize(
    "fault",
    [
        "product",
        "qa_head",
        "lock",
        "mode",
        "skip",
        "missing",
        "duplicate",
        "cleanup",
        "dirty",
        "paid",
    ],
)
def test_stale_partial_or_skipped_success_reports_cannot_pass(history, fault):
    root, _, fixed = history
    plan = runner.preflight(fixed, root=root, fix_sha=fixed)
    report = good_summary(plan)
    assert runner.check_summary(report, plan, "MIXED_DIAGNOSTIC")
    if fault == "product":
        report["product_sha"] = "0" * 40
    elif fault == "qa_head":
        report["qa_git_head"] = "0" * 40
    elif fault == "lock":
        report["environment"]["source_config_sha256"]["uv.lock"] = "wrong"
    elif fault == "mode":
        report["lifecycle_fixture_mode"] = "FRESH"
    elif fault == "skip":
        report["results"][0]["status"] = "SKIP"
    elif fault == "missing":
        report["results"].pop()
    elif fault == "duplicate":
        report["results"][-1] = report["results"][0]
    elif fault == "cleanup":
        report["resources_closed"] = False
    elif fault == "dirty":
        report["qa_git_dirty"] = True
    else:
        report["environment"]["paid_calls"] = 1
    assert not runner.check_summary(report, plan, "MIXED_DIAGNOSTIC")


def test_blocked_candidate_never_launches_the_runner(history, monkeypatch):
    root, old, fixed = history
    plan = runner.preflight(old, root=root, fix_sha=fixed)
    monkeypatch.setattr(runner, "run_once", lambda *a: pytest.fail("must not launch"))
    with pytest.raises(ValueError):
        runner.execute(plan, root=root)
    assert not (root / "build").exists()


@pytest.mark.parametrize("failed_index", [None, 0, 1])
def test_repeat_records_each_failure_and_stops_if_fresh_baseline_fails(
    history, monkeypatch, failed_index
):
    root, _, fixed = history
    plan = runner.preflight(fixed, root=root, fix_sha=fixed)
    monkeypatch.setattr(runner, "preflight", lambda *a, **k: plan)
    calls = []

    def simulated(root, plan, mode, directory):
        calls.append(mode)
        return {"mode": mode, "status": "FAIL" if len(calls) - 1 == failed_index else "PASS"}

    monkeypatch.setattr(runner, "run_once", simulated)
    result = runner.execute(plan, root=root)
    assert calls == ["FRESH"] + ([] if failed_index == 0 else ["MIXED_DIAGNOSTIC"] * 3)
    assert result["status"] == ("PASS_REQUIRES_B_C_REVIEW" if failed_index is None else "FAIL")
    if failed_index is not None:
        assert sum(r["status"] == "FAIL" for r in result["runs"]) == 1
    summary = next((root / "build/w5-d-g07").glob("*/summary.json"))
    assert json.loads(summary.read_text()) == result
    assert summary.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("mode", ["FRESH", "MIXED_DIAGNOSTIC"])
def test_candidate_and_mode_reach_the_locked_child_without_paid_key(history, monkeypatch, mode):
    from types import SimpleNamespace

    root, _, fixed = history
    plan = runner.preflight(fixed, root=root, fix_sha=fixed)
    monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_KEY_MUST_NOT_REACH_CHILD")
    monkeypatch.setenv("W5_D_MIXED_STACK_QA", "1")
    monkeypatch.setenv("GIT_DIR", "/unrelated/repository/.git")

    def child(args, *, cwd, env, stdout, stderr):
        assert args[:6] == ["uv", "run", "--all-packages", "--all-groups", "--locked", "python"]
        assert cwd == root and "OPENAI_API_KEY" not in env
        assert not any(key.startswith("GIT_") for key in env)
        assert env["W5_D_PRODUCT_SHA"] == fixed and env["LLM_PROVIDER"] == "mock"
        assert (env.get("W5_D_MIXED_STACK_QA") == "1") == (mode == "MIXED_DIAGNOSTIC")
        out = root / "child" / "synthetic-run"
        out.mkdir()
        (out / "summary.json").write_text(json.dumps(good_summary(plan, mode)))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", child)
    assert runner.run_once(root, plan, mode, root / "child")["status"] == "PASS"
