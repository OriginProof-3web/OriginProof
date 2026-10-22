"""Bounded opt-in evaluation; never retry uncertain calls."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import sys
import tempfile
from pathlib import Path
from statistics import median

import httpx
from openai import AsyncOpenAI
from originproof_core import wallet_contract

from .evidence_evaluation import CandidateEvidenceObserver
from .phishing_evaluation import classification_metrics, evaluate_phishing, load_corpus
from .providers import OpenAILLMProvider
from .settings import AnalyzerSettings

POLICY_KEYS = {
    "schema_version",
    "approved_for_paid_calls",
    "corpus_sha256",
    "model",
    "split",
    "review_reference",
    "budget_reference",
    "input_selection",
    "max_calls",
    "max_output_tokens",
    "output_token_budget",
    "max_input_characters",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def plan(path, policy):
    corpus = load_corpus(path)
    if set(policy) != POLICY_KEYS or policy["schema_version"] != "v5-d-live-policy-0.1":
        raise ValueError("policy schema")
    if type(policy["approved_for_paid_calls"]) is not bool:
        raise ValueError("approval type")
    if policy["model"] != "gpt-6-luna" or policy["split"] not in {"development", "holdout"}:
        raise ValueError("model or split")
    if policy["corpus_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("corpus identity")
    cases = [c for c in corpus["cases"] if c["split"] == policy["split"]]
    for key in ("max_calls", "max_output_tokens", "output_token_budget", "max_input_characters"):
        if type(policy[key]) is not int or policy[key] < 0:
            raise ValueError("budget type")
    if policy["max_calls"] > len(cases) or policy["max_output_tokens"] > 4096:
        raise ValueError("budget bounds")
    blocks = []
    if not policy["approved_for_paid_calls"]:
        blocks.append("PAID_SCOPE_NOT_APPROVED")
    if not all(
        isinstance(policy[k], str) and policy[k].strip()
        for k in ("review_reference", "budget_reference")
    ):
        blocks.append("REVIEW_OR_BUDGET_REFERENCE_MISSING")
    if (
        corpus.get("labels_human_reviewed") is not True
        or corpus.get("review_status") == "DRAFT_REVIEW_REQUIRED"
    ):
        blocks.append("LABELS_AND_SPLIT_REVIEW_PENDING")
    if policy["input_selection"] in {None, "", "UNDECIDED"} or policy[
        "input_selection"
    ] != corpus.get("input_selection"):
        blocks.append("INPUT_SELECTION_PENDING_OR_MISMATCH")
    if not all(
        policy[k] > 0
        for k in ("max_calls", "max_output_tokens", "output_token_budget", "max_input_characters")
    ):
        blocks.append("EXPLICIT_POSITIVE_LIMITS_REQUIRED")
    if any(len(c["text"]) > policy["max_input_characters"] for c in cases):
        blocks.append("INPUT_CHARACTER_LIMIT")
    return {
        "status": "BLOCKED" if blocks else "READY_NOT_EXECUTED",
        "blocks": blocks,
        "policy_sha256": digest(policy),
        "requested_cases": len(cases),
        "model": policy["model"],
        "split": policy["split"],
        "paid_calls": 0,
        "output_token_reservation_per_call": policy["max_output_tokens"],
        "money_cap": "NOT_ENFORCED_INPUT_AND_UNKNOWN_USAGE_NOT_PRICED",
    }


def save(path, value):
    """Atomically save private metrics and IDs without prompts or provider payloads."""
    payload = value | {"checksum": digest(value)}
    fd, temporary = tempfile.mkstemp(prefix=".d-eval-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_state(path, identity, ids):
    if path.is_symlink():
        raise ValueError("checkpoint symlink")
    state = json.loads(path.read_text())
    checksum = state.pop("checksum")
    if checksum != digest(state) or state["identity"] != identity:
        raise ValueError("checkpoint changed or incompatible")
    rows = state["rows"]
    if [r["id"] for r in rows] != ids[: len(rows)] or len(rows) > len(ids):
        raise ValueError("checkpoint case identity")
    for row in rows:
        if row["status"] not in {"DONE", "RESERVED", "UNKNOWN"}:
            raise ValueError("checkpoint status")
        if row["status"] == "RESERVED":
            # Preserve potentially billed reservations without replaying interrupted requests.
            row["status"] = "UNKNOWN"
    return state


class CappedTransport(httpx.AsyncBaseTransport):
    def __init__(self, inner, row, cap, checkpoint):
        self.inner, self.row, self.cap, self.checkpoint = inner, row, cap, checkpoint

    async def handle_async_request(self, request):
        if (
            str(request.url) != "https://api.openai.com/v1/responses"
            or request.method != "POST"
            or self.row["http_attempts"]
        ):
            raise ValueError("unexpected endpoint or repeated request")
        body = json.loads(request.content)
        if body.get("store") is not False or body.get("tools"):
            raise ValueError("unexpected storage or tools")
        body["max_output_tokens"] = self.cap
        self.row["http_attempts"] = 1
        self.checkpoint()
        bounded = httpx.Request(
            request.method,
            request.url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "content-length"},
            content=json.dumps(body).encode(),
            extensions=request.extensions,
        )
        response = await self.inner.handle_async_request(bounded)
        await response.aread()
        try:
            usage = response.json()["usage"]
            numeric = {k: usage[k] for k in ("input_tokens", "output_tokens", "total_tokens")}
            if not all(type(v) is int and v >= 0 for v in numeric.values()):
                raise ValueError("usage")
            self.row["usage"] = numeric
            self.row["usage_exceeds_output_cap"] = numeric["output_tokens"] > self.cap
        except (ValueError, KeyError, TypeError):
            self.row["usage"] = None
        self.checkpoint()
        return response

    async def aclose(self):
        await self.inner.aclose()


def summarize(state, cases):
    rows, latencies, counts = [], [], {}
    observer = CandidateEvidenceObserver(
        type("Metadata", (), {"provider_name": "openai", "model": "gpt-6-luna"})()
    )
    expected = {c["id"]: c for c in cases}
    completed = []
    for entry in state["rows"]:
        if entry["status"] == "DONE":
            result = entry["result"]
            completed.append(result)
            rows.extend(result["cases"])
            latencies.append(result["latency_seconds"]["p50"])
            evidence = result["evidence"]["candidate_grounding"]
            for key, value in evidence.items():
                if key in {
                    "candidate_quote_count",
                    "matched_candidate_quote_count",
                    "located_candidate_count",
                    "invalid_candidate_count",
                    "duplicate_candidate_count",
                    "covered_span_count",
                    "exact_span_match_count",
                    "observed_cases",
                    "unreadable_reports",
                }:
                    observer.counts[key] += value
        else:
            rows.append(
                {
                    "id": entry["id"],
                    "expected": expected[entry["id"]]["label"],
                    "predicted": None,
                    "error_code": "INTERRUPTED_OUTCOME_UNKNOWN",
                }
            )
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        counts[key] = sum((r.get("usage") or {}).get(key, 0) for r in state["rows"])
    return {
        "status": "COMPLETE" if len(rows) == len(cases) else "INCOMPLETE",
        "scope": state["identity"]["transport_scope"],
        "live_model_evaluated": state["identity"]["transport_scope"] == "OPENAI_HTTPS"
        and any(r["http_attempts"] for r in state["rows"]),
        "requested_cases": len(cases),
        "processed_cases": len(rows),
        "unknown_outcomes": sum(r["status"] != "DONE" for r in state["rows"]),
        "http_attempts": sum(r["http_attempts"] for r in state["rows"]),
        "reserved_calls": len(rows),
        "reserved_output_tokens": len(rows) * state["identity"]["output_cap"],
        "known_usage_only": counts,
        "usage_missing_cases": sum(r.get("usage") is None for r in state["rows"]),
        "output_cap_violation": any(r.get("usage_exceeds_output_cap") for r in state["rows"]),
        "combined_pipeline_classification": classification_metrics(rows),
        "model_unavailable_or_rejected": sum(r["model_unavailable_or_rejected"] for r in completed),
        "candidate_grounding": observer.metrics(
            expected_spans=sum(len(expected[r["id"]]["expected_evidence"]) for r in rows),
            total_cases=len(rows),
        ),
        "pipeline_latency_seconds_completed_only": {
            "timed_cases": len(latencies),
            "p50": median(latencies) if latencies else None,
            "p95": sorted(latencies)[max(0, (95 * len(latencies) + 99) // 100 - 1)]
            if latencies
            else None,
        },
        "acceptance_status": "REQUIRES_HUMAN_REVIEW_NOT_INPUT_OR_MODEL_ACCEPTANCE",
        "paid_cost": None,
    }


async def execute(path, policy, journal, *, api_key, resume=False, stop_after=None, transport=None):
    prepared = plan(path, policy)
    if prepared["blocks"]:
        raise ValueError("blocked policy")
    if not api_key or not api_key.strip() or (stop_after is not None and stop_after < 1):
        raise ValueError("execution configuration")
    cases = [c for c in load_corpus(path)["cases"] if c["split"] == policy["split"]]
    code = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (
            Path(__file__),
            Path(__file__).with_name("phishing_evaluation.py"),
            Path(__file__).with_name("providers.py"),
            Path(__file__).with_name("phishing.py"),
            Path(__file__).with_name("evidence_evaluation.py"),
            Path(__file__).with_name("settings.py"),
            Path(__file__).with_name("errors.py"),
            Path(__file__).with_name("inputs.py"),
            Path(wallet_contract.__file__),
            Path(wallet_contract.__file__).with_name("models.py"),
            Path(__file__).parent / "prompts/phishing_analysis_v1.md",
        )
    }
    identity = {
        "policy_sha256": prepared["policy_sha256"],
        "source_sha256": code,
        "transport_scope": "SDK_MOCK_TRANSPORT_TEST" if transport else "OPENAI_HTTPS",
        "output_cap": policy["max_output_tokens"],
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("openai", "httpx", "pydantic", "pydantic-settings")
        },
        "python": sys.version.split()[0],
    }
    journal.parent.mkdir(parents=True, exist_ok=True)
    lock = journal.with_name(journal.name + ".lock")
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        if resume:
            state = load_state(journal, identity, [c["id"] for c in cases])
        else:
            if journal.exists() or journal.is_symlink():
                raise ValueError("checkpoint already exists")
            state = {"schema_version": "v5-d-live-checkpoint-0.1", "identity": identity, "rows": []}
        save(journal, state)
        count = 0
        for case in cases[len(state["rows"]) :]:
            if any(r.get("usage_exceeds_output_cap") for r in state["rows"]):
                break
            reserved = len(state["rows"])
            if (
                reserved >= policy["max_calls"]
                or (reserved + 1) * policy["max_output_tokens"] > policy["output_token_budget"]
                or (stop_after is not None and count >= stop_after)
            ):
                break
            row = {"id": case["id"], "status": "RESERVED", "http_attempts": 0, "usage": None}
            state["rows"].append(row)
            save(journal, state)
            bounded = CappedTransport(
                transport or httpx.AsyncHTTPTransport(),
                row,
                policy["max_output_tokens"],
                lambda: save(journal, state),
            )
            async with AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.openai.com/v1",
                max_retries=0,
                http_client=httpx.AsyncClient(
                    transport=bounded, trust_env=False, follow_redirects=False
                ),
            ) as client:
                provider = OpenAILLMProvider(
                    AnalyzerSettings(
                        openai_model="gpt-6-luna", llm_max_retries=0, openai_reasoning_effort="low"
                    ),
                    async_client=client,
                )
                row["result"] = await evaluate_phishing(
                    path,
                    provider=provider,
                    split=policy["split"],
                    case_ids=[case["id"]],
                )
            row["status"] = "DONE"
            save(journal, state)
            count += 1
            if row.get("usage_exceeds_output_cap"):
                break
        state["summary"] = summarize(state, cases)
        save(journal, state)
        return state["summary"]
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after", type=int)
    args = parser.parse_args()
    try:
        policy = json.loads(args.policy.read_text())
        prepared = plan(args.manifest, policy)
        if not args.execute or prepared["blocks"]:
            print(json.dumps(prepared))
            return 2 if args.execute else 0
        summary = asyncio.run(
            execute(
                args.manifest,
                policy,
                args.journal,
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                resume=args.resume,
                stop_after=args.stop_after,
            )
        )
        print(json.dumps(summary, ensure_ascii=False))
        return (
            0
            if (
                summary["status"] == "COMPLETE"
                and not summary["output_cap_violation"]
                and not summary["unknown_outcomes"]
                and not summary["model_unavailable_or_rejected"]
            )
            else 1
        )
    except KeyboardInterrupt:
        print(json.dumps({"status": "INTERRUPTED_CHECK_PRIVATE_JOURNAL"}))
        return 130
    except Exception:
        print(json.dumps({"status": "INVALID_POLICY_OR_CHECKPOINT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
