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


@pytest.fixture
def response_body():
    def build(data, *, status="completed", refusal=False, empty=False):
        part = (
            {"type": "refusal", "refusal": "PRIVATE_REFUSAL"}
            if refusal
            else {
                "type": "output_text",
                "text": json.dumps(data),
                "annotations": [],
            }
        )
        return {
            "id": "resp_test_only",
            "object": "response",
            "created_at": 0,
            "status": status,
            "model": "configured-model",
            "error": None,
            "incomplete_details": (
                {"reason": "max_output_tokens"} if status == "incomplete" else None
            ),
            "output": []
            if empty
            else [
                {
                    "id": "msg_test",
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [part],
                }
            ],
            "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
        }

    return build
