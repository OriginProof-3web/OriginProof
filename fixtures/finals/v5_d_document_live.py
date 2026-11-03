"""Manually approved development images only; default CLI plans without an API key."""

import argparse
import asyncio
import json
import logging
from pathlib import Path

import httpx
from dotenv import dotenv_values
from openai import AsyncOpenAI
from originproof_analyzer.document_evaluation import evaluate_document_images
from originproof_analyzer.live_evaluation import CappedTransport, digest, save
from originproof_analyzer.media_converters import document_image_to_text
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import OpenAILLMProvider
from originproof_analyzer.settings import AnalyzerSettings

CAPS = {"CONVERSION": 4096, "ANALYSIS": 1024}
MAX_CALLS = 46
OUTPUT_RESERVATION = 117760


class ImageBudgetTransport(httpx.AsyncBaseTransport):
    """Reserve before send; a duplicate or uncertain outcome cannot spend again."""

    def __init__(self, journal, case_ids, inner=None):
        self.journal = Path(journal)
        self.case_ids = tuple(case_ids)
        self.stage = None
        self.inner = inner if inner is not None else httpx.AsyncHTTPTransport()
        self.lock = asyncio.Lock()

    async def handle_async_request(self, request):
        async with self.lock:
            state = json.loads(self.journal.read_text())
            checksum = state.pop("checksum")
            if checksum != digest(state) or state["approved_for_paid_calls"] is not True:
                raise ValueError("unapproved or altered image checkpoint")
            rows = state["rows"]
            if len(rows) >= MAX_CALLS or any(
                row.get("http_status") != 200
                or row.get("usage") is None
                or row.get("usage_exceeds_output_cap")
                for row in rows
            ):
                raise ValueError("image quota consumed or previous outcome uncertain")
            if self.stage is None:
                raise ValueError("image stage required")
            case_id, stage = self.stage
            if case_id not in self.case_ids or stage not in CAPS:
                raise ValueError("unapproved image stage")
            used = {(row["case_id"], row["stage"]) for row in rows}
            if self.stage in used or (stage == "ANALYSIS" and (case_id, "CONVERSION") not in used):
                raise ValueError("duplicate or out-of-order image stage")
            body = json.loads(request.content)
            if body.get("model") != "gpt-6-luna":
                raise ValueError("unapproved image model")
            image = any(
                item.get("type") == "input_image"
                for message in body.get("input", [])
                if isinstance(message, dict)
                for item in message.get("content", [])
                if isinstance(item, dict)
            )
            if image != (stage == "CONVERSION"):
                raise ValueError("image payload does not match stage")
            row = {"case_id": case_id, "stage": stage, "http_attempts": 0, "usage": None}
            rows.append(row)
            save(self.journal, state)
            return await CappedTransport(
                self.inner, row, CAPS[stage], lambda: save(self.journal, state)
            ).handle_async_request(request)

    async def aclose(self):
        await self.inner.aclose()


async def execute(policy_path, journal, *, api_key):
    policy = json.loads(policy_path.read_text())
    plan = await evaluate_document_images()
    if (
        policy["approved_for_paid_calls"] is not True
        or policy["model"] != "gpt-6-luna"
        or policy["max_calls"] != MAX_CALLS
        or policy["output_token_reservation"] != OUTPUT_RESERVATION
        or policy["output_caps"] != CAPS
        or policy["asset_manifest_sha256"] != plan["asset_manifest_sha256"]
        or plan["selected_images"] != 23
        or not api_key
        or journal.exists()
        or journal.is_symlink()
    ):
        raise ValueError("fresh journal, exact scope and explicit image approval required")
    ids = [row["id"] for row in plan["cases"]]
    state = {
        "approved_for_paid_calls": True,
        "policy_sha256": digest(policy),
        "asset_manifest_sha256": plan["asset_manifest_sha256"],
        "case_ids": ids,
        "max_calls": MAX_CALLS,
        "rows": [],
    }
    journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation also refuses concurrent callers before any network request.
    with journal.open("x"):
        journal.chmod(0o600)
    save(journal, state)
    transport = ImageBudgetTransport(journal, ids)
    settings = AnalyzerSettings(
        llm_provider="openai", openai_model="gpt-6-luna",
        openai_reasoning_effort="low", llm_max_retries=0,
    )
    index = -1
    try:
        async with (
            httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=False) as http,
            AsyncOpenAI(
                api_key=api_key, base_url="https://api.openai.com/v1",
                max_retries=0, http_client=http,
            ) as client,
        ):
            analyzer = PhishingAnalyzer(OpenAILLMProvider(settings, async_client=client))

            async def convert(artifact):
                nonlocal index
                index += 1
                transport.stage = (ids[index], "CONVERSION")
                return await document_image_to_text(
                    artifact, settings=settings, client=client, enabled=True,
                )

            async def analyze(text):
                transport.stage = (ids[index], "ANALYSIS")
                return await analyzer(text)

            report = await evaluate_document_images(converter=convert, processor=analyze)
    finally:
        state = json.loads(journal.read_text())
        state.pop("checksum")
        state["approved_for_paid_calls"] = False
        save(journal, state)
        policy["approved_for_paid_calls"] = False
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n")
    rows = state["rows"]
    usage = {
        key: sum((row.get("usage") or {}).get(key, 0) for row in rows)
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    report.update(
        scope="ACTUAL_OPENAI_DEVELOPMENT_IMAGES_NOT_PRODUCT_ACCEPTANCE",
        model="gpt-6-luna", reasoning_effort="low", paid_calls=len(rows),
        prior_paid_calls=87, cumulative_paid_calls=87 + len(rows),
        max_retries=0, output_token_reservation=OUTPUT_RESERVATION,
        usage=usage, request_rows=rows, checkpoint_closed=True,
        journal_checksum=json.loads(journal.read_text())["checksum"],
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for name in ("httpx", "httpcore", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    if args.execute:
        if any(value is None for value in (args.policy, args.journal, args.key_file, args.output)):
            parser.error("execute requires policy, fresh journal, local key file and output")
        if args.output.exists() or args.output.is_symlink():
            parser.error("output already exists")
        key = dotenv_values(args.key_file, interpolate=False).get("OPENAI_API_KEY")
        report = asyncio.run(execute(args.policy, args.journal, api_key=key))
    else:
        report = asyncio.run(evaluate_document_images())
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            args.output.chmod(0o600)
            stream.write(content)
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
