"""Opt-in D loopback QA composition. Never a production entrypoint or image upload contract."""

import asyncio
import base64
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
from dotenv import dotenv_values
from fastapi import Depends, Request
from openai import AsyncOpenAI
from originproof_analyzer.converted_inputs import analyze_conversion
from originproof_analyzer.inputs import SemanticInput
from originproof_analyzer.live_evaluation import CappedTransport, digest, save
from originproof_analyzer.media_converters import document_image_to_text
from originproof_analyzer.phishing import PhishingAnalyzer
from originproof_analyzer.providers import MockLLMProvider, OpenAILLMProvider
from originproof_analyzer.settings import AnalyzerSettings
from originproof_api.accounts import current_session
from originproof_api.main import create_app
from originproof_api.settings import Settings

STAGES = ("TEXT_SMOKE", "IMAGE_CONVERSION", "IMAGE_ANALYSIS")
CAPS = (1024, 4096, 1024)


class SmokeTransport(httpx.AsyncBaseTransport):
    """Reserve one of three approved requests before sending; unknown outcomes are never replayed."""

    def __init__(self, journal, inner=None):
        self.journal = Path(journal)
        self.inner = inner or httpx.AsyncHTTPTransport()
        self.lock = asyncio.Lock()

    async def handle_async_request(self, request):
        async with self.lock:
            state = json.loads(self.journal.read_text())
            checksum = state.pop("checksum")
            if checksum != digest(state) or state["approved_for_paid_calls"] is not True:
                raise ValueError("unapproved or altered smoke checkpoint")
            rows = state["rows"]
            if len(rows) >= 3 or any(
                r.get("http_status") != 200
                or r.get("usage") is None
                or r.get("usage_exceeds_output_cap")
                for r in rows
            ):
                raise ValueError("smoke quota consumed or previous outcome uncertain")
            image = any(
                item.get("type") == "input_image"
                for message in json.loads(request.content).get("input", [])
                if isinstance(message, dict)
                for item in message.get("content", [])
                if isinstance(item, dict)
            )
            index = len(rows)
            if image != (index == 1):
                raise ValueError("unexpected smoke stage")
            row = {"stage": STAGES[index], "http_attempts": 0, "usage": None}
            rows.append(row)
            save(self.journal, state)
            capped = CappedTransport(
                self.inner, row, CAPS[index], lambda: save(self.journal, state)
            )
            return await capped.handle_async_request(request)

    async def aclose(self):
        await self.inner.aclose()


def process_app():
    if os.environ.get("D_CONNECTED_QA") != "1":
        raise RuntimeError("loopback synthetic QA only")
    mode = os.environ.get("D_CONNECTED_MODE", "none")
    if mode not in {"none", "mock", "live"}:
        raise ValueError("unsupported smoke mode")
    app = create_app(settings=Settings(_env_file=None))
    original_lifespan = app.router.lifespan_context
    client = None

    @asynccontextmanager
    async def lifespan(application):
        nonlocal client
        if mode == "mock":
            application.state.analysis_processor = PhishingAnalyzer(MockLLMProvider())
        elif mode == "live":
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            values = dotenv_values(os.environ["D_LOCAL_KEY_FILE"], interpolate=False)
            key = values.get("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("local key unavailable")
            client = AsyncOpenAI(
                api_key=key,
                max_retries=0,
                http_client=httpx.AsyncClient(
                    transport=SmokeTransport(os.environ["D_SMOKE_JOURNAL"]),
                    trust_env=False,
                    follow_redirects=False,
                ),
            )
            application.state.analysis_processor = PhishingAnalyzer(
                OpenAILLMProvider(AnalyzerSettings(llm_max_retries=0), async_client=client)
            )
        try:
            async with original_lifespan(application):
                yield
        finally:
            if client is not None:
                await client.close()

    app.router.lifespan_context = lifespan

    # QA-only authenticated bridge: proves converter→processor over TCP without inventing /v3 API.
    @app.post("/__d_qa/document", include_in_schema=False)
    async def document(request: Request, account: Annotated[tuple, Depends(current_session)]):
        if mode != "live":
            raise RuntimeError("live QA bridge disabled")
        artifact = SemanticInput(
            image_base64=base64.b64encode(await request.body()).decode(),
            image_media_type=request.headers.get("content-type"),
        )
        configured = AnalyzerSettings(llm_provider="openai", llm_max_retries=0)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 180
        async with asyncio.timeout_at(deadline):
            conversion = await document_image_to_text(
                artifact,
                settings=configured,
                client=client,
                enabled=True,
                remaining_seconds=deadline - loop.time(),
            )
            analyzed = await analyze_conversion(
                conversion, app.state.analysis_processor, remaining_seconds=deadline - loop.time()
            )
        return {"qa_only": True, "report": analyzed.report.model_dump(mode="json")}

    return app
