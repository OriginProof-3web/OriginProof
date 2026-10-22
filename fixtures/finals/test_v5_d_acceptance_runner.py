"""No green subsets or synthetic-to-actual promotion in the D acceptance evidence runner."""

import json
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest
from v5_d_acceptance_runner import ROOT, SUITES, evidence, execute


def junit(path, modules):
    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root,
        "testsuite",
        tests=str(sum(n for _, n in modules)),
        failures="0",
        errors="0",
        skipped="0",
    )
    for module, count in modules:
        for i in range(count):
            ET.SubElement(
                suite, "testcase", classname="fixtures.finals." + Path(module).stem, name=f"case{i}"
            )
    ET.ElementTree(root).write(path)
    return root


@pytest.mark.parametrize(
    "change",
    [
        None,
        "skip",
        "summary",
        "duplicate",
        "missing_name",
        "missing_module",
        "root_summary",
        "root_failures",
    ],
)
def test_strict_module_identity_and_junit_denominators(tmp_path, change):
    p = tmp_path / "report.xml"
    root = junit(p, [("alpha.py", 2)])
    cases = list(root.iter("testcase"))
    if change == "skip":
        ET.SubElement(cases[0], "skipped")
    elif change == "summary":
        root.find("testsuite").set("tests", "100")
    elif change == "duplicate":
        cases[1].set("name", cases[0].get("name"))
    elif change == "missing_name":
        cases[0].attrib.pop("name")
    elif change == "missing_module":
        cases[0].set("classname", "other")
    elif change == "root_summary":
        root.set("tests", "999")
    elif change == "root_failures":
        root.set("failures", "1")
    ET.ElementTree(root).write(p)
    assert evidence(p, 2, ["alpha.py"])["status"] == ("PASS" if change is None else "FAIL")


@pytest.mark.parametrize("child_failure", [False, True])
def test_all_synthetic_pass_keeps_21_actual_acceptance_items_blocked(tmp_path, child_failure):
    stage = [
        line
        for line in (ROOT / "fixtures/finals/v5_d_stage_qa_files.txt").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    plan = {
        "qa_sha": "a" * 40,
        "suites": {
            name: {"modules": stage if name == "stage" else files, "expected_tests": n}
            for name, (files, n) in SUITES.items()
        },
    }
    calls = []

    def child(args, **kwargs):
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert kwargs["env"]["LLM_PROVIDER"] == "mock"
        calls.append(args)
        xml = Path(next(a.split("=", 1)[1] for a in args if a.startswith("--junitxml=")))
        # pytest arguments have a fixed --junitxml boundary; commands are not read from a manifest.
        files = args[next(i + 1 for i, a in enumerate(args) if a.startswith("--junitxml=")) :]
        sizes = [12, 13, 6, 12] if len(files) == 4 else [plan["suites"][xml.stem]["expected_tests"]]
        junit(xml, list(zip(files, sizes, strict=True)))
        return SimpleNamespace(returncode=1 if child_failure and xml.stem == "benchmark" else 0)

    result = execute(plan, tmp_path / "output", run=child)
    assert len(calls) == 4 and len(result["acceptance"]) == 21
    assert all(
        a["actual_acceptance"] == "BLOCKED" and not a["stage_accepted"]
        for a in result["acceptance"]
    )
    assert result["status"] == (
        "FAIL" if child_failure else "SUPPORTING_SUITES_PASS_ACCEPTANCE_BLOCKED"
    )
    assert json.loads((tmp_path / "output/summary.json").read_text())["paid_calls"] == 0
    assert (tmp_path / "output/summary.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError):
        execute(plan, tmp_path / "output", run=child)
