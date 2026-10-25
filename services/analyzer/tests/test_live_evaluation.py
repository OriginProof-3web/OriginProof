"""Paid-run safety via the real SDK over MockTransport; no actual model calls or human approvals."""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import httpx
import pytest
from originproof_analyzer import live_evaluation as live

CORPUS = Path(__file__).resolve().parents[3] / "fixtures/synthetic/phishing_sources_v1.json"


@pytest.fixture
def prepared(tmp_path):
    data = json.loads(CORPUS.read_text())
    # Disposable simulated approval, never authorization for actual paid calls.
    data.update(labels_human_reviewed=True, review_status="TEST_ONLY", input_selection="TEXT")
    path = tmp_path / "test-corpus.json"
    path.write_text(json.dumps(data))
    policy = {
        "schema_version": "v5-d-live-policy-0.1",
        "approved_for_paid_calls": True,
        "corpus_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "model": "gpt-6-luna",
        "split": "development",
        "review_reference": "SIMULATED_TEST",
        "budget_reference": "SIMULATED_TEST",
        "input_selection": "TEXT",
        "max_calls": 24,
        "max_output_tokens": 64,
        "output_token_budget": 1536,
        "max_input_characters": 1000,
    }
    return path, policy, tmp_path / "private-journal.json"


def response(response_body):
    return response_body(
        {
            "risk_level": "UNDETERMINED",
            "evidence": [],
            "limitations": [],
            "verification": None,
            "verification_not_run_reason": "ANALYZER_DOES_NOT_VERIFY",
        }
    )


def test_draft_plan_never_constructs_client_or_creates_checkpoint(tmp_path, monkeypatch, capsys):
    draft = json.loads(CORPUS.read_text())
    draft.update(labels_human_reviewed=False, review_status="DRAFT_REVIEW_REQUIRED")
    draft_path = tmp_path / "unreviewed.json"
    draft_path.write_text(json.dumps(draft))
    _, policy, journal = (tmp_path / "x", {}, tmp_path / "never.json")
    policy = {
        "schema_version": "v5-d-live-policy-0.1",
        "approved_for_paid_calls": False,
        "corpus_sha256": hashlib.sha256(draft_path.read_bytes()).hexdigest(),
        "model": "gpt-6-luna",
        "split": "development",
        "review_reference": "",
        "budget_reference": "",
        "input_selection": "UNDECIDED",
        "max_calls": 0,
        "max_output_tokens": 0,
        "output_token_budget": 0,
        "max_input_characters": 0,
    }
    file = tmp_path / "policy.json"
    file.write_text(json.dumps(policy))
    monkeypatch.setattr(live, "AsyncOpenAI", lambda **k: pytest.fail("no SDK client during plan"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval",
            "--manifest",
            str(draft_path),
            "--policy",
            str(file),
            "--journal",
            str(journal),
            "--execute",
        ],
    )
    assert live.main() == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED" and result["paid_calls"] == 0
    assert "LABELS_AND_SPLIT_REVIEW_PENDING" in result["blocks"]
    assert not journal.exists()


@pytest.mark.parametrize(
    "key,value",
    [
        ("max_calls", True),
        ("max_calls", 25),
        ("max_output_tokens", 4097),
        ("model", "other"),
        ("corpus_sha256", "bad"),
        ("split", "all"),
    ],
)
def test_invalid_or_mismatched_policy(prepared, key, value):
    path, policy, _ = prepared
    policy[key] = value
    with pytest.raises(ValueError):
        live.plan(path, policy)


async def test_stop_resume_has_unique_cases_exact_caps_private_checkpoint(
    prepared, response_body, monkeypatch
):
    path, policy, journal = prepared
    seen = []

    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "gpt-6-luna" and body["max_output_tokens"] == 64
        assert body["store"] is False and "tools" not in body
        text = body["input"][0]["content"][0]["text"]
        seen.append(text)
        assert text in [c["text"] for c in live.load_corpus(path)["cases"]]
        assert "expected_evidence" not in body and "label" not in body
        return httpx.Response(200, json=response(response_body))

    for resume in (False, True):
        result = await live.execute(
            path,
            policy,
            journal,
            api_key="PRIVATE_API_KEY",
            resume=resume,
            stop_after=2,
            transport=httpx.MockTransport(handler),
        )
    assert len(seen) == len(set(seen)) == result["processed_cases"] == 4
    assert result["http_attempts"] == 4 and result["reserved_output_tokens"] == 256
    assert result["known_usage_only"]["output_tokens"] == 136
    assert result["status"] == "INCOMPLETE" and result["scope"] == "SDK_MOCK_TRANSPORT_TEST"
    assert result["live_model_evaluated"] is False
    assert journal.stat().st_mode & 0o777 == 0o600
    stored = journal.read_text()
    assert "PRIVATE_API_KEY" not in stored and all(text not in stored for text in seen)
    assert not journal.with_name(journal.name + ".lock").exists()
    installed_version = live.importlib.metadata.version
    monkeypatch.setattr(
        live.importlib.metadata,
        "version",
        lambda name: "different-runtime" if name == "httpx" else installed_version(name),
    )
    with pytest.raises(ValueError):
        await live.execute(
            path,
            policy,
            journal,
            api_key="PRIVATE_API_KEY",
            resume=True,
            transport=httpx.MockTransport(lambda r: pytest.fail("no mixed-runtime replay")),
        )


@pytest.mark.parametrize("failure", ["429", "503", "timeout"])
async def test_failed_calls_are_charged_and_never_retried(prepared, response_body, failure):
    path, policy, journal = prepared
    seen = []

    def handler(request):
        seen.append(1)
        if failure == "timeout":
            raise httpx.ReadTimeout("PRIVATE_PAYLOAD", request=request)
        return httpx.Response(int(failure), json={"error": {"message": "PRIVATE_PAYLOAD"}})

    result = await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        stop_after=2,
        transport=httpx.MockTransport(handler),
    )
    assert len(seen) == result["reserved_calls"] == result["http_attempts"] == 2
    assert result["reserved_output_tokens"] == 128 and result["usage_missing_cases"] == 2
    assert result["model_unavailable_or_rejected"] == 2
    assert "PRIVATE_PAYLOAD" not in journal.read_text()


async def test_output_budget_reserves_full_cap_not_observed_usage(prepared, response_body):
    path, policy, journal = prepared
    policy["output_token_budget"] = 64
    result = await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response(response_body))),
    )
    assert result["http_attempts"] == result["processed_cases"] == 1
    assert result["known_usage_only"]["output_tokens"] == 34
    assert result["reserved_output_tokens"] == 64 and result["status"] == "INCOMPLETE"


async def test_interrupted_call_is_unknown_and_not_replayed_on_resume(prepared, response_body):
    path, policy, journal = prepared
    seen = []

    def interrupt(request):
        seen.append(json.loads(request.content)["input"])
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await live.execute(
            path, policy, journal, api_key="placeholder", transport=httpx.MockTransport(interrupt)
        )

    def succeed(request):
        seen.append(json.loads(request.content)["input"])
        return httpx.Response(200, json=response(response_body))

    result = await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        resume=True,
        stop_after=1,
        transport=httpx.MockTransport(succeed),
    )
    assert len(seen) == 2 and seen[0] != seen[1]
    assert result["unknown_outcomes"] == 1 and result["reserved_calls"] == 2
    assert result["candidate_grounding"]["total_cases"] == 2
    assert result["pipeline_latency_seconds_completed_only"]["timed_cases"] == 1
    assert result["combined_pipeline_classification"]["confusion_matrix"]["HIGH"]["ERROR"] == 1
    assert json.loads(journal.read_text())["rows"][0]["status"] == "UNKNOWN"


@pytest.mark.parametrize("change", ["checksum", "policy", "lock"])
async def test_incompatible_or_locked_resume_is_rejected_before_http(
    prepared, response_body, change
):
    path, policy, journal = prepared
    await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        stop_after=1,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response(response_body))),
    )
    if change == "checksum":
        state = json.loads(journal.read_text())
        state["rows"][0]["id"] = "DIFFERENT"
        journal.write_text(json.dumps(state))
    elif change == "policy":
        policy["max_calls"] = 2
    else:
        journal.with_name(journal.name + ".lock").touch()
    with pytest.raises((ValueError, FileExistsError)):
        await live.execute(
            path,
            policy,
            journal,
            api_key="placeholder",
            resume=True,
            transport=httpx.MockTransport(lambda r: pytest.fail("no HTTP")),
        )


async def test_provider_usage_above_cap_stops_further_requests(prepared, response_body):
    path, policy, journal = prepared
    body = response(response_body)
    body["usage"]["output_tokens"] = 65
    result = await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)),
    )
    assert result["output_cap_violation"] and result["http_attempts"] == 1
    resumed = await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        resume=True,
        transport=httpx.MockTransport(lambda r: pytest.fail("cap violation must halt resumes")),
    )
    assert resumed["http_attempts"] == 1


async def test_selected_case_ids_cannot_cross_split_or_disappear():
    with pytest.raises(ValueError):
        await live.evaluate_phishing(CORPUS, case_ids=["NONEXISTENT"])


def test_recorded_development_plan_retains_paid_approval_gate():
    fixtures = CORPUS.parent
    policy = json.loads(
        (fixtures / "v5_d_live_evaluation_policy.development.pending.json").read_text()
    )
    assert policy["approved_for_paid_calls"] is False
    assert (
        policy["max_calls"],
        policy["max_output_tokens"],
        policy["output_token_budget"],
        policy["max_input_characters"],
    ) == (24, 1024, 24576, 200)
    result = live.plan(CORPUS, policy)
    assert result["blocks"] == ["PAID_SCOPE_NOT_APPROVED"]
    assert result["paid_calls"] == 0
    example = json.loads((fixtures / "v5_d_live_evaluation_policy.example.json").read_text())
    assert example["approved_for_paid_calls"] is False and example["max_calls"] == 0


@pytest.mark.parametrize(
    "status,code,expected",
    [
        (404, "model_not_found", "model_not_found"),
        (401, "invalid_api_key", "invalid_api_key"),
        (429, "insufficient_quota", "insufficient_quota"),
        (400, "PRIVATE_SECRET_CODE", "UNCLASSIFIED"),
        (503, {"private": "PRIVATE_SECRET"}, "UNCLASSIFIED"),
    ],
)
async def test_http_diagnostics_never_persist_provider_message_or_unknown_code(
    prepared, status, code, expected
):
    path, policy, journal = prepared
    result = await live.execute(
        path,
        policy,
        journal,
        api_key="placeholder",
        stop_after=1,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                status, json={"error": {"code": code, "message": "PRIVATE_SECRET_MESSAGE"}}
            )
        ),
    )
    stored = journal.read_text()
    row = json.loads(stored)["rows"][0]
    assert row["http_status"] == status and row["provider_error_code"] == expected
    assert "PRIVATE_SECRET" not in stored
    assert result["http_attempts"] == 1 and result["live_model_evaluated"] is False
