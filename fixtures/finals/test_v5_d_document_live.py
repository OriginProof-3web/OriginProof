"""Image request ledger checks: no API key or network, all responses are synthetic."""

import json
import socket

import httpx
import pytest
import v5_d_document_live as batch
from originproof_analyzer.live_evaluation import save
from v5_d_document_live import CAPS, ImageBudgetTransport


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def blocked(*args, **kwargs):
        pytest.fail("image budget tests cannot access network")

    monkeypatch.setattr(socket.socket, "connect", blocked)


def request(image=False, **changes):
    return httpx.Request("POST", "https://api.openai.com/v1/responses", json={
        "model": "gpt-6-luna", "store": False,
        "input": [{"role": "user", "content": [
            {"type": "input_image" if image else "input_text"}
        ]}],
        **changes,
    })


async def test_23_images_at_most_46_attempts_and_exact_reserved_caps(tmp_path):
    journal = tmp_path / "ledger.json"
    save(journal, {"approved_for_paid_calls": True, "rows": []})
    ids = [f"DP-{index}" for index in range(23)]
    seen = []

    def handler(req):
        # Reservation must already be durable when the actual HTTP transport runs.
        assert len(json.loads(journal.read_text())["rows"]) == len(seen) + 1
        seen.append(json.loads(req.content)["max_output_tokens"])
        return httpx.Response(200, json={"usage": {
            "input_tokens": 1, "output_tokens": 2, "total_tokens": 3
        }})

    transport = ImageBudgetTransport(journal, ids, httpx.MockTransport(handler))
    for case_id in ids:
        for stage in CAPS:
            transport.stage = (case_id, stage)
            await transport.handle_async_request(request(stage == "CONVERSION"))
    assert len(seen) == 46 and sum(seen) == 117760
    assert seen == [4096, 1024] * 23
    with pytest.raises(ValueError, match="quota consumed"):
        await transport.handle_async_request(request())
    assert journal.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("fault", ["http", "usage", "timeout", "cap"])
async def test_uncertain_outcome_blocks_all_later_images(tmp_path, fault):
    journal = tmp_path / "ledger.json"
    save(journal, {"approved_for_paid_calls": True, "rows": []})
    seen = []

    def handler(req):
        seen.append(1)
        if fault == "timeout":
            raise httpx.ReadTimeout("private error", request=req)
        return httpx.Response(503 if fault == "http" else 200, json={}
                              if fault == "usage" else {"usage": {
                                  "input_tokens": 1,
                                  "output_tokens": 4097 if fault == "cap" else 2,
                                  "total_tokens": 4098 if fault == "cap" else 3,
                              }})

    transport = ImageBudgetTransport(journal, ["one", "two"], httpx.MockTransport(handler))
    transport.stage = ("one", "CONVERSION")
    try:
        await transport.handle_async_request(request(True))
    except httpx.ReadTimeout:
        pass
    transport.stage = ("two", "CONVERSION")
    with pytest.raises(ValueError, match="uncertain"):
        await transport.handle_async_request(request(True))
    assert len(seen) == 1


async def test_execution_error_closes_approval_and_journal_and_never_replays(tmp_path, monkeypatch):
    policy = tmp_path / "policy.json"
    journal = tmp_path / "ledger.json"
    policy.write_text(json.dumps({
        "approved_for_paid_calls": True, "model": "gpt-6-luna",
        "max_calls": 46, "output_token_reservation": 117760,
        "output_caps": CAPS, "asset_manifest_sha256": "synthetic-hash",
    }))
    planned = {"selected_images": 23, "asset_manifest_sha256": "synthetic-hash",
               "cases": [{"id": f"DP-{i}"} for i in range(23)]}

    async def evaluation(**callbacks):
        if callbacks:
            raise RuntimeError("synthetic evaluator failure before any request")
        return planned

    monkeypatch.setattr(batch, "evaluate_document_images", evaluation)
    with pytest.raises(RuntimeError, match="synthetic evaluator"):
        await batch.execute(policy, journal, api_key="synthetic-unused-key")
    closed = json.loads(journal.read_text())
    assert closed["approved_for_paid_calls"] is False and closed["rows"] == []
    assert json.loads(policy.read_text())["approved_for_paid_calls"] is False
    with pytest.raises(ValueError, match="fresh journal"):
        await batch.execute(policy, journal, api_key="synthetic-unused-key")


async def test_model_stage_duplicate_closed_and_tampered_checkpoints_cannot_spend(tmp_path):
    journal = tmp_path / "ledger.json"
    state = {"approved_for_paid_calls": True, "rows": []}
    save(journal, state)
    seen = []

    def handler(req):
        seen.append(1)
        return httpx.Response(200, json={"usage": {
            "input_tokens": 1, "output_tokens": 2, "total_tokens": 3
        }})

    transport = ImageBudgetTransport(journal, ["one"], httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="stage required"):
        await transport.handle_async_request(request(True))
    transport.stage = ("one", "ANALYSIS")
    with pytest.raises(ValueError, match="out-of-order"):
        await transport.handle_async_request(request())
    transport.stage = ("one", "CONVERSION")
    with pytest.raises(ValueError, match="model"):
        await transport.handle_async_request(request(True, model="unapproved"))
    with pytest.raises(ValueError, match="payload"):
        await transport.handle_async_request(request())
    assert not seen
    await transport.handle_async_request(request(True))
    with pytest.raises(ValueError, match="duplicate"):
        await transport.handle_async_request(request(True))
    state = json.loads(journal.read_text())
    state.pop("checksum")
    state["approved_for_paid_calls"] = False
    save(journal, state)
    with pytest.raises(ValueError, match="unapproved"):
        await transport.handle_async_request(request(True))
    state["approved_for_paid_calls"] = True
    journal.write_text(json.dumps(state | {"checksum": "altered"}))
    with pytest.raises(ValueError, match="altered"):
        await transport.handle_async_request(request(True))
    assert len(seen) == 1
