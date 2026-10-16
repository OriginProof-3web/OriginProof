import json
import socket
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "mvp"


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def no_network(*args, **kwargs):
        raise AssertionError("Analyzer tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)


@pytest.fixture
def cases():
    return json.loads((FIXTURE_ROOT / "analyzer_cases.json").read_text())["cases"]


@pytest.fixture
def normal_case(cases):
    return next(case for case in cases if case["id"] == "normal")
