"""Validate exact D QA counts and zero skips/failures; no live services."""

import argparse
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

STAGE_MODULE_COUNT = 4  # Required cumulative D modules on this PR.
STAGE_COUNTS = {
    "v5_d_w2_governance_qa": 12,
    "v5_d_w3_content_qa": 13,
    "v5_d_w4_lifecycle_qa": 6,
    "v5_d_analysis_integration_qa": 12,
}


def check_report(path: Path, suite: str) -> dict[str, int]:
    minimums = (
        dict(list(STAGE_COUNTS.items())[:STAGE_MODULE_COUNT])
        if suite == "stage"
        else {"v5_analysis_consumer_qa": 31}
    )
    if suite == "stage":
        manifest = Path(__file__).with_name("v5_d_stage_qa_files.txt").read_text().splitlines()
        listed = [line for line in manifest if line.strip() and not line.startswith("#")]
        expected = {f"fixtures/finals/{name}.py" for name in minimums}
        if len(listed) != len(expected) or set(listed) != expected:
            raise ValueError("stage manifest must contain the required QA files exactly once")
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError("missing or malformed D QA JUnit report") from error
    for node in root.iter():
        if node.tag in {"failure", "error", "skipped"}:
            raise ValueError("D QA must have zero failures, errors and skips")
        if node.tag in {"testsuite", "testsuites"} and any(
            int(node.get(key, "0")) != 0 for key in ("failures", "errors", "skipped")
        ):
            raise ValueError("D QA suite summary reports a failure, error or skip")
        if node.tag == "testsuite" or (node.tag == "testsuites" and "tests" in node.attrib):
            actual = sum(1 for _ in node.iter("testcase"))
            try:
                total = int(node.attrib["tests"])
            except (KeyError, ValueError) as error:
                raise ValueError("D QA suite must report an integer test count") from error
            if total != actual:
                raise ValueError(
                    f"D QA suite test count disagrees with testcases: {total} != {actual}"
                )
    counts, seen = Counter(), set()
    for case in root.iter("testcase"):
        identity = (case.get("classname"), case.get("name"))
        if not all(identity) or identity in seen:
            raise ValueError("missing or duplicate D QA test identity")
        seen.add(identity)
        counts[case.get("classname")] += 1
    expected_counts = {f"fixtures.finals.{name}": count for name, count in minimums.items()}
    if set(counts) != set(expected_counts):
        raise ValueError("D QA JUnit has missing or unexpected test modules")
    for name, minimum in expected_counts.items():
        if counts[name] != minimum:
            raise ValueError(
                f"D QA test count differs from expectation: {name}: {counts[name]} != {minimum}"
            )
    return dict(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--suite", choices=["stage", "consumer"], required=True)
    args = parser.parse_args()
    result = check_report(args.report, args.suite)
    print(f"D {args.suite} evidence: {sum(result.values())} tests, zero failures/errors/skips")
