"""Execute existing synthetic D suites and bind supporting evidence to one clean QA commit."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

from v5_d_junit_guard import STAGE_COUNTS
from v5_d_junit_guard import check_report as validate_junit

ROOT = Path(__file__).resolve().parents[2]
SUITES = {
    "stage": ([], 43),
    "consumer": (["fixtures/finals/v5_analysis_consumer_qa.py"], 31),
    "benchmark": (["fixtures/finals/test_v5_d_verification_benchmark.py"], 16),
    "independent": (["fixtures/finals/test_v5_d_independent_verifier.py"], 22),
}
SUPPORT = {
    "stage": list(range(1, 12)) + [15, 16, 17],
    "consumer": [15, 16, 17],
    "independent": [4, 5, 7, 8, 9, 13, 20],
}


def evidence(path, expected, modules):
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    identities = [(c.get("classname"), c.get("name")) for c in cases]
    counts = {kind: len(list(root.iter(kind))) for kind in ("failure", "error", "skipped")}
    module_names = {c.get("classname", "").rsplit(".", 1)[-1] for c in cases}
    summaries = list(root.iter("testsuite"))
    if root.tag == "testsuites" and any(
        key in root.attrib for key in ("tests", "failures", "errors", "skipped")
    ):
        summaries.insert(0, root)
    valid_summary = (
        root.tag in {"testsuite", "testsuites"}
        and ("tests" not in root.attrib or int(root.get("tests")) == len(cases))
        and bool(summaries)
    ) and all(
        int(s.get("tests", "-1")) == len(list(s.iter("testcase")))
        and all(
            int(s.get(k, "0")) == len(list(s.iter(tag)))
            for k, tag in (("failures", "failure"), ("errors", "error"), ("skipped", "skipped"))
        )
        for s in summaries
    )
    passed = (
        len(cases) == expected
        and len(set(identities)) == expected
        and all(all(identity) for identity in identities)
        and not any(counts.values())
        and valid_summary
        and module_names == {Path(m).stem for m in modules}
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "tests": len(cases),
        **counts,
        "expected_tests": expected,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def prepare(root):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip():
        raise ValueError("clean worktree required")
    suites = {k: (list(v[0]), v[1]) for k, v in SUITES.items()}
    suites["stage"] = (
        [
            x
            for x in (root / "fixtures/finals/v5_d_stage_qa_files.txt").read_text().splitlines()
            if x and not x.startswith("#")
        ],
        43,
    )
    if len(suites["stage"][0]) != 4 or set(suites["stage"][0]) != {
        f"fixtures/finals/{m}.py" for m in STAGE_COUNTS
    }:
        raise ValueError("four required stage modules")
    for modules, _ in suites.values():
        if any(not (root / m).is_file() for m in modules):
            raise ValueError("missing required QA file")
    return {
        "qa_sha": head,
        "lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "python": sys.version.split()[0],
        "packages": {
            k: importlib.metadata.version(k)
            for k in ("pytest", "httpx", "openai", "fastapi", "sqlalchemy")
        },
        "scope": "ASGI_SQLITE_SYNTHETIC_REGISTRY_AND_RPC_NOT_ACTUAL_ACCEPTANCE",
        "suites": {k: {"modules": m, "expected_tests": n} for k, (m, n) in suites.items()},
    }


def execute(plan, output, *, root=ROOT, run=subprocess.run):
    if output.exists() or output.is_symlink():
        raise ValueError("output exists")
    output.mkdir(parents=True, mode=0o700)
    env = dict(os.environ, LLM_PROVIDER="mock")
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = ":".join(
        str(root / p)
        for p in (
            "fixtures/finals",
            "apps/api/tests",
            "apps/api/src",
            "packages/python",
            "services/analyzer/src",
            "services/indexer/src",
        )
    )
    rows = {}
    for name, suite in plan["suites"].items():
        xml = output / f"{name}.xml"
        log = output / f"{name}.log"
        try:
            with log.open("x") as stream:
                log.chmod(0o600)
                child = run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "-o",
                        "addopts=",
                        f"--junitxml={xml}",
                        *suite["modules"],
                    ],
                    cwd=root,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=300,
                )
        except (OSError, subprocess.SubprocessError):
            rows[name] = {"status": "FAIL", "detail": "CHILD_EXECUTION_FAILED"}
            continue
        try:
            row = evidence(xml, suite["expected_tests"], suite["modules"])
            if name in {"stage", "consumer"}:
                validate_junit(xml, name)
            if child.returncode:
                row["status"] = "FAIL"
        except (ValueError, OSError, ET.ParseError):
            row = {"status": "FAIL", "detail": "INVALID_OR_MISSING_EVIDENCE"}
        rows[name] = row
    status = "SUPPORTING_SUITES_PASS_ACCEPTANCE_BLOCKED"
    if any(r["status"] != "PASS" for r in rows.values()):
        status = "FAIL"
    source_consistent = True
    if "lock_sha256" in plan:
        current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
        source_consistent = (
            current == plan["qa_sha"]
            and not subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip()
            and hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest() == plan["lock_sha256"]
        )
        if not source_consistent:
            status = "FAIL"
    acceptance = []
    # Reuse the work inventory without declaring actual acceptance.
    source = json.loads((root / "docs/qa/v5-d-weekly-status-20261021.json").read_text())
    for item in source["acceptance"]:
        number = int(item["id"].removeprefix("V5-F"))
        relevant = [name for name, ids in SUPPORT.items() if number in ids]
        acceptance.append(
            {
                "id": item["id"],
                "supporting_suites": relevant,
                "supporting_status": "FAIL"
                if any(rows[n]["status"] != "PASS" for n in relevant)
                else "PASS"
                if relevant
                else "NOT_RUN",
                "actual_acceptance": "BLOCKED",
                "stage_accepted": False,
                "remaining": item["remaining"],
            }
        )
    report = plan | {
        "status": status,
        "executed": True,
        "results": rows,
        "source_consistent": source_consistent,
        "acceptance": acceptance,
        "paid_calls": 0,
        "g07": "USE_SEPARATE_FIXED_PRODUCT_REPORT_AND_B_C_REVIEW",
        "missing_actual_evidence": [
            "selected input/model evaluation",
            "wallet/browser/Registry integration",
            "actual RPC performance/independent verifier",
            "other physical laptop",
            "same RC rehearsals x3",
            "human review",
        ],
    }
    path = output / "summary.json"
    with path.open("x") as stream:
        path.chmod(0o600)
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        plan = prepare(ROOT)
        if not args.execute:
            print(json.dumps(plan | {"executed": False}))
            return 0
        output = args.output or ROOT / "build/qa" / ("d-acceptance-" + uuid4().hex)
        report = execute(plan, output)
        print(json.dumps({"status": report["status"], "report": str(output / "summary.json")}))
        return (
            1 if report["status"] == "FAIL" else 2
        )  # Supporting PASS never opens the release gate.
    except (ValueError, OSError, subprocess.SubprocessError):
        print(json.dumps({"status": "INVALID_ACCEPTANCE_CONFIGURATION_OR_EXECUTION"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
