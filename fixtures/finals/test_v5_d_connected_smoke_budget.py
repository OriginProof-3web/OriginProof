"""Offline SDK transport budget guard; fake responses only, never a model call."""

import json
import socket

import httpx
import pytest
from originproof_analyzer.live_evaluation import save
from v5_d_connected_smoke import SmokeTransport


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def blocked(*args, **kwargs):
        pytest.fail("budget guard tests cannot access network")

    monkeypatch.setattr(socket.socket, "connect", blocked)


def request(image=False, **changes):
    body = {
        "model": "gpt-6-luna",
        "store": False,
        "max_output_tokens": 4096,
        "input": [
            {"role": "user", "content": [{"type": "input_image" if image else "input_text"}]}
        ],
        **changes,
    }
    return httpx.Request("POST", "https://api.openai.com/v1/responses", json=body)


async def test_exact_three_stages_caps_and_no_fourth_or_closed_policy(tmp_path):
    journal = tmp_path / "ledger.json"
    seen = []
    save(journal, {"approved_for_paid_calls": True, "rows": []})

    def handler(req):
        seen.append(json.loads(req.content)["max_output_tokens"])
        return httpx.Response(
            200, json={"usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}}
        )

    transport = SmokeTransport(journal, httpx.MockTransport(handler))
    for image in [False, True, False]:
        await transport.handle_async_request(request(image))
    assert seen == [1024, 4096, 1024]
    with pytest.raises(ValueError, match="quota consumed"):
        await transport.handle_async_request(request())
    state = json.loads(journal.read_text())
    state.pop("checksum")
    state["approved_for_paid_calls"] = False
    save(journal, state)
    with pytest.raises(ValueError, match="unapproved"):
        await transport.handle_async_request(request())
    assert len(seen) == 3


@pytest.mark.parametrize("failure", ["http", "usage", "timeout", "cap"])
async def test_unknown_or_failed_response_prevents_next_request(tmp_path, failure):
    journal = tmp_path / "ledger.json"
    save(journal, {"approved_for_paid_calls": True, "rows": []})
    seen = []

    def handler(req):
        seen.append(1)
        if failure == "timeout":
            raise httpx.ReadTimeout("private detail", request=req)
        return httpx.Response(
            503 if failure == "http" else 200,
            json={}
            if failure == "usage"
            else {
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 2000 if failure == "cap" else 2,
                    "total_tokens": 2001 if failure == "cap" else 3,
                }
            },
        )

    transport = SmokeTransport(journal, httpx.MockTransport(handler))
    try:
        await transport.handle_async_request(request())
    except httpx.ReadTimeout:
        pass
    with pytest.raises(ValueError, match="uncertain"):
        await transport.handle_async_request(request(True))
    assert len(seen) == 1


async def test_wrong_model_or_stage_cannot_send_anything(tmp_path):
    journal = tmp_path / "ledger.json"
    save(journal, {"approved_for_paid_calls": True, "rows": []})

    def forbidden(req):
        pytest.fail("unapproved payload reached transport")

    transport = SmokeTransport(journal, httpx.MockTransport(forbidden))
    with pytest.raises(ValueError, match="model"):
        await transport.handle_async_request(request(model="unapproved"))
    with pytest.raises(ValueError, match="stage"):
        await transport.handle_async_request(request(True))
    assert json.loads(journal.read_text())["rows"] == []
