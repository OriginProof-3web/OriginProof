"""Member AI keys: encrypted at rest, never echoed, and only that member's jobs use them."""

import asyncio
import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from originproof_analyzer import anthropic_provider
from originproof_analyzer.errors import AnalyzerError, AnalyzerErrorCode
from originproof_api.ai_keys import member_ai_key, usage_hook
from originproof_api.database import AccountAiKeyRow
from originproof_api.main import create_app
from originproof_api.main import member_ai as production_member_ai
from pydantic import SecretStr
from sqlalchemy import select

pytest_plugins = ("test_wallet_runtime",)

CLAUDE_KEY = "sk-ant-" + "a" * 30 + "WXYZ"
GPT_KEY = "sk-" + "b" * 30 + "QRST"
TEXT = "원격지원 앱을 설치하세요"


@pytest.fixture
async def api(wallet):
    used = []

    def member_ai(provider, key, usage):
        async def processor(text):
            used.append((provider, key))
            usage["input"], usage["output"] = 120, 30
            raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE)

        return processor, None

    settings = wallet.app.state.settings.model_copy(
        update={
            "signup_enabled": True,
            "wallet_text_input_enabled": True,
            "ai_key_secret": SecretStr("s" * 40),
        }
    )
    app = create_app(database=wallet.app.state.database, settings=settings, member_ai=member_ai)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = "keyuser@example.invalid"
        body = {
            "kind": "personal",
            "email": email,
            "password": "synthetic1pass",
            "terms_accepted": True,
        }
        assert (await client.post("/v1/auth/register", json=body)).status_code == 201
        login = await client.post(
            "/v1/auth/login", json={"username": email, "password": body["password"]}
        )
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        yield SimpleNamespace(
            client=client, app=app, used=used, account_id=login.json()["account_id"]
        )


async def test_key_is_encrypted_write_only_and_replaceable(api):
    assert (await api.client.get("/v1/auth/ai-key")).json() == {
        "provider": None,
        "hint": None,
        "storage_enabled": True,
        "input_tokens": 0,
        "output_tokens": 0,
        "analyses": 0,
    }
    saved = await api.client.post(
        "/v1/auth/ai-key", json={"provider": "anthropic", "key": CLAUDE_KEY}
    )
    assert saved.status_code == 200 and CLAUDE_KEY not in saved.text
    assert saved.json()["hint"] == "WXYZ"
    async with api.app.state.database.session_factory() as db:
        row = await db.scalar(select(AccountAiKeyRow))
    assert CLAUDE_KEY.encode() not in row.ciphertext
    assert await member_ai_key(api.app, api.account_id) == ("anthropic", CLAUDE_KEY)
    await api.client.post("/v1/auth/ai-key", json={"provider": "openai", "key": GPT_KEY})
    assert await member_ai_key(api.app, api.account_id) == ("openai", GPT_KEY)
    assert (await api.client.delete("/v1/auth/ai-key")).json()["provider"] is None
    assert await member_ai_key(api.app, api.account_id) is None


@pytest.mark.parametrize(
    "body,status,code",
    [
        ({"provider": "openai", "key": CLAUDE_KEY}, 422, "INVALID_AI_KEY"),
        ({"provider": "anthropic", "key": GPT_KEY}, 422, "INVALID_AI_KEY"),
        ({"provider": "anthropic", "key": "sk-ant-short"}, 422, "INVALID_AI_KEY"),
    ],
)
async def test_wrong_key_is_rejected_without_echo(api, body, status, code):
    response = await api.client.post("/v1/auth/ai-key", json=body)
    assert (response.status_code, response.json()["detail"]) == (status, code)
    assert body["key"] not in response.text


async def test_malformed_body_does_not_echo_key(api):
    response = await api.client.post(
        "/v1/auth/ai-key", json={"provider": "other", "key": CLAUDE_KEY}
    )
    assert response.status_code == 422 and CLAUDE_KEY not in response.text


async def test_write_requires_csrf_and_login(api):
    token = api.client.headers.pop("X-CSRF-Token")
    body = {"provider": "anthropic", "key": CLAUDE_KEY}
    assert (await api.client.post("/v1/auth/ai-key", json=body)).status_code == 403
    assert (await api.client.delete("/v1/auth/ai-key")).status_code == 403
    api.client.headers["X-CSRF-Token"] = token
    api.client.cookies.clear()
    assert (await api.client.get("/v1/auth/ai-key")).status_code == 401


async def test_no_server_secret_refuses_storage(api, wallet):
    settings = api.app.state.settings.model_copy(update={"ai_key_secret": None})
    api.app.state.settings = settings
    response = await api.client.post(
        "/v1/auth/ai-key", json={"provider": "anthropic", "key": CLAUDE_KEY}
    )
    assert (response.status_code, response.json()["detail"]) == (409, "AI_KEY_STORAGE_DISABLED")


async def test_tampered_or_undecryptable_key_never_falls_back(api):
    await api.client.post("/v1/auth/ai-key", json={"provider": "anthropic", "key": CLAUDE_KEY})
    async with api.app.state.database.session_factory() as db:
        row = await db.scalar(select(AccountAiKeyRow))
        row.provider = "openai"
        await db.commit()
    with pytest.raises(AnalyzerError) as caught:
        await member_ai_key(api.app, api.account_id)
    assert caught.value.code == AnalyzerErrorCode.PROVIDER_UNAVAILABLE


async def test_analysis_job_uses_only_the_members_key(api):
    async def server_default(text):
        api.used.append(("server", None))
        raise AnalyzerError(AnalyzerErrorCode.PROVIDER_UNAVAILABLE)

    api.app.state.analysis_processor = server_default

    async def run(request_id):
        ref = await api.client.post("/v3/inputs", json={"kind": "TEXT", "text": TEXT})
        job = await api.client.post(
            "/v3/analyses", json={"request_id": request_id, "input_ref": ref.json()["input_ref"]}
        )
        assert job.status_code == 202, job.text
        await asyncio.gather(*api.app.state.analysis_tasks, return_exceptions=True)

    await run("req_without_member_key")
    assert api.used == [("server", None)]
    api.used.clear()
    await api.client.post("/v1/auth/ai-key", json={"provider": "anthropic", "key": CLAUDE_KEY})
    await run("req_with_member_key")
    assert api.used == [("anthropic", CLAUDE_KEY)]
    seen = (await api.client.get("/v1/auth/ai-key")).json()
    assert (seen["input_tokens"], seen["output_tokens"], seen["analyses"]) == (120, 30, 1)
    await api.client.post("/v1/auth/ai-key", json={"provider": "openai", "key": GPT_KEY})
    reset = (await api.client.get("/v1/auth/ai-key")).json()
    assert (reset["input_tokens"], reset["output_tokens"], reset["analyses"]) == (0, 0, 0)


def test_member_ai_builds_the_requested_provider():
    for provider, key in (("anthropic", CLAUDE_KEY), ("openai", GPT_KEY)):
        processor, converter = production_member_ai(provider, key, {"input": 0, "output": 0})
        assert callable(processor) and callable(converter)
    assert CLAUDE_KEY not in repr(
        production_member_ai("anthropic", CLAUDE_KEY, {"input": 0, "output": 0})
    )


class _FakeMessages:
    def __init__(self, message):
        self.message, self.calls = message, []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.message, Exception):
            raise self.message
        return self.message


def _fake_client(message):
    messages = _FakeMessages(message)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    client.with_options = lambda **_: client
    return client, messages


def _message(text=None, stop_reason="end_turn"):
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(stop_reason=stop_reason, content=content)


@pytest.mark.parametrize(
    "message,code",
    [
        (_message(stop_reason="refusal"), AnalyzerErrorCode.REFUSAL),
        (_message(stop_reason="max_tokens"), AnalyzerErrorCode.INCOMPLETE_OUTPUT),
        (_message(), AnalyzerErrorCode.INCOMPLETE_OUTPUT),
        (_message("not json"), AnalyzerErrorCode.SCHEMA_MISMATCH),
        (_message(json.dumps({"partial": True})), AnalyzerErrorCode.SCHEMA_MISMATCH),
    ],
)
async def test_claude_provider_fails_closed(message, code):
    client, _ = _fake_client(message)
    provider = anthropic_provider.AnthropicLLMProvider(
        anthropic_provider.AnthropicSettings(), client
    )
    with pytest.raises(AnalyzerError) as caught:
        await provider.analyze_phishing(TEXT)
    assert caught.value.code == code


async def test_claude_provider_maps_connection_errors_without_key():
    problem = anthropic.APIConnectionError(request=SimpleNamespace())
    client, _ = _fake_client(problem)
    provider = anthropic_provider.AnthropicLLMProvider(
        anthropic_provider.AnthropicSettings(), client
    )
    with pytest.raises(AnalyzerError) as caught:
        await provider.analyze_phishing(TEXT)
    assert caught.value.code == AnalyzerErrorCode.PROVIDER_UNAVAILABLE
    assert caught.value.__cause__ is None


async def test_claude_request_shape_is_pinned():
    client, messages = _fake_client(_message(stop_reason="refusal"))
    settings = anthropic_provider.AnthropicSettings()
    with pytest.raises(AnalyzerError):
        await anthropic_provider.AnthropicLLMProvider(settings, client).analyze_phishing(TEXT)
    sent = messages.calls[0]
    assert sent["model"] == settings.anthropic_model == "claude-opus-5-5"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["fallbacks"] == "default"
    assert sent["messages"][0]["content"] == [{"type": "text", "text": TEXT}]


def test_claude_client_is_pinned_to_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://attacker.invalid")
    client = anthropic_provider.member_client(CLAUDE_KEY)
    assert str(client.base_url).startswith("https://api.anthropic.com")
    assert client._client.follow_redirects is False


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (200, {"usage": {"input_tokens": 11, "output_tokens": 7}}, {"input": 11, "output": 7}),
        (200, {"output": []}, {"input": 0, "output": 0}),
        (401, {"usage": {"input_tokens": 99, "output_tokens": 9}}, {"input": 0, "output": 0}),
    ],
)
async def test_usage_hook_counts_only_successful_reported_tokens(status, body, expected):
    usage = {"input": 0, "output": 0}
    await usage_hook(usage)(httpx.Response(status, json=body))
    assert usage == expected


async def test_usage_hook_ignores_non_json():
    usage = {"input": 0, "output": 0}
    await usage_hook(usage)(httpx.Response(200, content=b"not json"))
    assert usage == {"input": 0, "output": 0}
