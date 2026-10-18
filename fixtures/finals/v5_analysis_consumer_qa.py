"""Run explicitly against an immutable C candidate export, never the legacy API.

PYTHONPATH=<candidate>/apps/api/src:<candidate>/packages/python \
  <candidate>/.uv-venv/bin/python -m pytest -q -o addopts= \
  fixtures/finals/v5_analysis_consumer_qa.py

This file is outside normal pytest testpaths. It uses injected reports and no network.
"""

import json
import socket
from copy import deepcopy
from pathlib import Path

import pytest
from originproof_api.wallet_analyses import ground_report
from originproof_core.wallet_contract import REVISION
from pydantic import ValidationError

MANIFEST = json.loads(
    (Path(__file__).resolve().parents[1] / "synthetic/analysis_consumer_cases_v1.json")
    .read_text(encoding="utf-8")
)


@pytest.fixture(autouse=True)
def no_live_services(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("D analysis consumer QA must not use network services")

    monkeypatch.setattr(socket.socket, "connect", blocked)


def test_candidate_contract_revision():
    assert REVISION == MANIFEST["candidate_contract"]


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda c: c["id"])
def test_analysis_consumer_contract(case):
    value = deepcopy(case["report"])
    expected = case["expected"]
    if not expected["accepted"]:
        if expected["error"] == "SCHEMA_MISMATCH":
            with pytest.raises(ValidationError):
                ground_report(value, case["text"])
        else:
            with pytest.raises(ValueError, match="^" + expected["error"] + "$"):
                ground_report(value, case["text"])
    else:
        actual = ground_report(value, case["text"])
        assert actual.risk_level == value["risk_level"]
        assert actual.verification is None
        assert actual.verification_not_run_reason == "NO_DOCUMENT_REFERENCE"
        assert actual.limitations == value["limitations"]
        assert [[e.start_offset, e.end_offset] for e in actual.evidence] == expected["ranges"]
        assert [e.quote for e in actual.evidence] == [e["quote"] for e in value["evidence"]]
        assert [e.source for e in actual.evidence] == [e["source"] for e in value["evidence"]]
    assert value == case["report"]
