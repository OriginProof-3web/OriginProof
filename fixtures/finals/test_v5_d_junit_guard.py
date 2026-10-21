"""Regression checks for missing, reduced, skipped and failed D QA evidence."""

from xml.etree import ElementTree as ET

import pytest
from v5_d_junit_guard import check_report


@pytest.fixture
def report(tmp_path):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", failures="0", errors="0", skipped="0")
    for name, count in [
        ("v5_d_w2_governance_qa", 12),
        ("v5_d_w3_content_qa", 13),
        ("v5_d_w4_lifecycle_qa", 6),
        ("v5_d_analysis_integration_qa", 12),
    ]:
        for index in range(count):
            ET.SubElement(suite, "testcase", classname=f"fixtures.finals.{name}", name=str(index))
    path = tmp_path / "stage.xml"
    return root, suite, path


def test_complete_stage_report_is_accepted(report):
    root, _, path = report
    ET.ElementTree(root).write(path)
    assert sum(check_report(path, "stage").values()) == 43


@pytest.mark.parametrize(
    "fault",
    ["missing_module", "fewer_tests", "skipped", "failure", "error", "duplicate", "summary"],
)
def test_invalid_evidence_cannot_pass(report, fault):
    root, suite, path = report
    first = suite[0]
    if fault == "missing_module":
        for case in list(suite)[:12]:
            suite.remove(case)
    elif fault == "fewer_tests":
        suite.remove(first)
    elif fault in {"skipped", "failure", "error"}:
        ET.SubElement(first, fault)
    elif fault == "duplicate":
        suite.append(ET.fromstring(ET.tostring(first)))
    else:
        suite.set("skipped", "1")
    ET.ElementTree(root).write(path)
    with pytest.raises(ValueError):
        check_report(path, "stage")


@pytest.mark.parametrize("body", [None, "<broken"])
def test_missing_or_malformed_junit_cannot_pass(tmp_path, body):
    path = tmp_path / "consumer.xml"
    if body is not None:
        path.write_text(body)
    with pytest.raises(ValueError):
        check_report(path, "consumer")


def test_consumer_count_cannot_drop_to_a_small_green_subset(tmp_path):
    root = ET.Element("testsuite", failures="0", errors="0", skipped="0")
    path = tmp_path / "consumer.xml"
    for index in range(31):
        ET.SubElement(
            root, "testcase", classname="fixtures.finals.v5_analysis_consumer_qa", name=str(index)
        )
    ET.ElementTree(root).write(path)
    assert sum(check_report(path, "consumer").values()) == 31
    root.remove(root[0])
    ET.ElementTree(root).write(path)
    with pytest.raises(ValueError, match="test count decreased"):
        check_report(path, "consumer")
