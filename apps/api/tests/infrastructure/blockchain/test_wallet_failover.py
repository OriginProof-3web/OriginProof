"""Runtime wallet RPC switching with synthetic JSON-RPC nodes (mock; no live chain claimed)."""

import asyncio
import json
import logging
import socket
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from eth_abi import encode
from eth_utils import keccak
from fastapi import HTTPException
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_failover import FailoverWalletRpc
from originproof_api.main import create_app
from originproof_api.settings import Settings
from originproof_api.wallet_runtime import WalletRuntime
from originproof_core import DependencyUnavailableError

ROOT = Path(__file__).resolve().parents[5]
ABI = json.loads((ROOT / "packages/contracts/abi/OriginProofWalletRegistry.json").read_text())
ADDRESS = "0x" + "12" * 20
DEPLOYMENT_HASH, HEAD_HASH = "0x" + "11" * 32, "0x" + "22" * 32
CODE = b"runtime"
# 키가 들어간 provider URL을 흉내 낸다. 로그·예외 어디에도 나오면 안 된다.
PRIMARY, FALLBACK = "http://primary.test/v3/SECRETKEY1", "http://fallback.test/v3/SECRETKEY2"
ISSUER = b"\x01" * 32


class Node:
    def __init__(self):
        self.mode = "ok"
        self.calls = []
        self.chain_id, self.deployment_hash, self.code = "0x7a69", DEPLOYMENT_HASH, CODE
        self.call_result = 5

    def handle(self, request):
        payload = json.loads(request.content)
        method, params = payload["method"], payload["params"]
        self.calls.append(method)
        if self.mode == "down":
            raise httpx.ConnectError(f"connection refused {request.url}", request=request)
        if self.mode == "timeout":
            raise httpx.ReadTimeout(f"timed out {request.url}", request=request)
        if self.mode == "http_error":
            # raise_for_status() builds an HTTPStatusError whose message carries the full URL.
            return httpx.Response(500, request=request)
        blocks = {
            "0x1": {"number": "0x1", "hash": self.deployment_hash, "timestamp": "0x64"},
            "0x2": {"number": "0x2", "hash": HEAD_HASH, "timestamp": "0x65"},
        }
        result = {
            "eth_chainId": lambda: self.chain_id,
            "eth_getBlockByNumber": lambda: blocks["0x2" if params[0] == "latest" else params[0]],
            "eth_getCode": lambda: "0x" + self.code.hex(),
            "eth_call": lambda: "0x" + encode(["uint256"], [self.call_result]).hex(),
            "eth_sendRawTransaction": lambda: "0x" + "ab" * 32,
        }[method]()
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})


@pytest.fixture
async def chain():
    primary, fallback = Node(), Node()
    hosts = {"primary.test": primary, "fallback.test": fallback}
    now = [1000.0]
    transport = httpx.MockTransport(lambda request: hosts[request.url.host].handle(request))
    async with httpx.AsyncClient(transport=transport) as client:
        rpc = FailoverWalletRpc(
            client,
            (PRIMARY, FALLBACK),
            clock=lambda: now[0],
            chain_id=31337,
            address=ADDRESS,
            deployment_block=1,
            deployment_hash=DEPLOYMENT_HASH,
            runtime_code_hash="0x" + keccak(CODE).hex(),
            abi=ABI,
        )
        yield SimpleNamespace(rpc=rpc, primary=primary, fallback=fallback, now=now)


async def nonce(rpc):
    return (await rpc.read("nextNonce", [ISSUER]))["values"][0]


@pytest.mark.parametrize("failure", ["down", "timeout", "wrong_chain", "wrong_code"])
async def test_primary_failure_reads_from_verified_fallback(chain, failure):
    if failure == "wrong_chain":
        chain.primary.chain_id = "0x1"
    elif failure == "wrong_code":
        chain.primary.code = b"other"
    else:
        chain.primary.mode = failure
    assert await nonce(chain.rpc) == 5
    assert chain.rpc.on_fallback
    # 보조는 같은 호출 전에 chain ID·배포 블록·런타임 코드 검사(snapshot)를 먼저 통과했다.
    assert chain.fallback.calls[:4] == [
        "eth_chainId",
        "eth_getBlockByNumber",
        "eth_getBlockByNumber",
        "eth_getCode",
    ]
    assert "eth_call" in chain.fallback.calls


@pytest.mark.parametrize("fault", ["chain_id", "deployment_hash", "code"])
async def test_unverified_fallback_is_never_used(chain, fault):
    chain.primary.mode = "down"
    if fault == "chain_id":
        chain.fallback.chain_id = "0x1"
    elif fault == "deployment_hash":
        chain.fallback.deployment_hash = "0x" + "99" * 32
    else:
        chain.fallback.code = b"other"
    with pytest.raises(DependencyUnavailableError):
        await nonce(chain.rpc)
    assert "eth_call" not in chain.fallback.calls and not chain.rpc.on_fallback


async def test_both_failing_is_503_not_a_fake_result(chain):
    chain.primary.mode = chain.fallback.mode = "down"
    with pytest.raises(DependencyUnavailableError):
        await nonce(chain.rpc)
    runtime = WalletRuntime(None, SimpleNamespace(), WalletRegistryReadAdapter(chain.rpc))
    with pytest.raises(HTTPException) as exc:
        await runtime.rpc("key", "0x" + "ab" * 32)
    assert exc.value.status_code == 503 and exc.value.detail == "WALLET_REGISTRY_UNAVAILABLE"


async def test_submission_uses_primary_only(chain):
    chain.primary.mode = "down"
    assert await nonce(chain.rpc) == 5 and chain.rpc.on_fallback
    # 보조 사용 중이어도 제출은 주로만, 실패해도 보조로 다시 보내지 않는다.
    with pytest.raises(DependencyUnavailableError):
        await chain.rpc.rpc("eth_sendRawTransaction", ["0x01"])
    assert "eth_sendRawTransaction" not in chain.fallback.calls
    chain.primary.mode = "ok"
    assert await chain.rpc.rpc("eth_sendRawTransaction", ["0x01"]) == "0x" + "ab" * 32
    assert chain.primary.calls.count("eth_sendRawTransaction") == 2
    assert "eth_sendRawTransaction" not in chain.fallback.calls


async def test_primary_is_retried_after_fallback_window(chain):
    chain.primary.mode = "down"
    assert await nonce(chain.rpc) == 5
    chain.primary.mode, chain.primary.calls = "ok", []
    chain.now[0] += 59
    assert await nonce(chain.rpc) == 5
    assert chain.primary.calls == [] and chain.rpc.on_fallback
    chain.now[0] += 1
    fallback_calls = len(chain.fallback.calls)
    assert await nonce(chain.rpc) == 5
    assert "eth_call" in chain.primary.calls and not chain.rpc.on_fallback
    assert len(chain.fallback.calls) == fallback_calls


# --- URL 비노출: 로거 이름으로 거르지 않고 루트 DEBUG 전체를 본다 -----------------------------

SECRETS = ("SECRETKEY1", "SECRETKEY2", "primary.test", "fallback.test", "/v3/SECRET")
DOCUMENT = "0x" + "cd" * 32


def everything_logged(caplog):
    """Every record any logger produced, formatted with arguments and tracebacks."""
    formatter = logging.Formatter("%(name)s %(levelname)s %(message)s")
    return "\n".join(formatter.format(record) for record in caplog.records)


def exception_chain(error):
    """All exceptions reachable through __cause__/__context__, recursively."""
    seen, stack, text = set(), [error], []
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        text.append(f"{current!s} {current!r} {current.args!r}")
        stack += [current.__cause__, current.__context__]
    return "\n".join(text), len(seen)


def assert_no_secret(*texts):
    joined = "\n".join(texts)
    for secret in SECRETS:
        assert secret not in joined, secret


def document_app(rpc):
    settings = Settings(_env_file=None, wallet_registry_address=ADDRESS)

    async def dispose():
        pass

    database = SimpleNamespace(dispose=dispose, session_factory=None)
    return create_app(
        database=database, settings=settings, wallet_chain=WalletRegistryReadAdapter(rpc)
    )


async def get_document(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://api.test") as client:
        return await client.get(f"/v3/documents/{DOCUMENT}")


@pytest.mark.parametrize("failure", ["down", "timeout", "http_error"])
async def test_primary_failure_to_fallback_exposes_no_url(chain, caplog, failure):
    caplog.set_level(logging.DEBUG)  # 루트 기준 전체 캡처
    chain.primary.mode = failure
    chain.primary.call_result = chain.fallback.call_result = 0  # 문서 없음 → 404
    response = await get_document(document_app(chain.rpc))
    # 보조로 정상 응답했으므로 경계 밖으로 나온 예외가 없다(빈 체인).
    assert response.status_code == 404 and response.json() == {"detail": "DOCUMENT_NOT_FOUND"}
    assert chain.rpc.on_fallback and "eth_call" in chain.fallback.calls
    logs = everything_logged(caplog)
    assert "wallet RPC primary failed" in logs and "switched to fallback" in logs
    assert_no_secret(response.text, str(response.headers), logs)


@pytest.mark.parametrize("failure", ["down", "timeout", "http_error"])
async def test_both_failing_503_exposes_no_url(chain, caplog, failure):
    caplog.set_level(logging.DEBUG)
    chain.primary.mode = chain.fallback.mode = failure
    response = await get_document(document_app(chain.rpc))
    assert response.status_code == 503
    assert response.json() == {"detail": "WALLET_REGISTRY_UNAVAILABLE"}
    chains = []
    runtime = WalletRuntime(None, SimpleNamespace(), WalletRegistryReadAdapter(chain.rpc))
    for call in (
        runtime.rpc("key", "0x" + "ab" * 32),  # API 경계(HTTPException)
        nonce(chain.rpc),  # 전환 RPC 직접
        chain.rpc.rpc("eth_sendRawTransaction", ["0x01"]),  # 제출(주만)
    ):
        with pytest.raises((HTTPException, DependencyUnavailableError)) as exc:
            await call
        text, _ = exception_chain(exc.value)
        chains.append(text)
    logs = everything_logged(caplog)
    assert "wallet RPC primary failed" in logs and "wallet RPC fallback failed" in logs
    assert_no_secret(response.text, str(response.headers), logs, *chains)


async def test_real_tcp_transport_logs_expose_no_url(caplog):
    """Real httpx/httpcore transport (no MockTransport): httpcore DEBUG traces carry the host."""
    node = Node()
    node.call_result = 0

    async def serve(reader, writer):
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            length = next(
                int(line.split(b":")[1])
                for line in head.split(b"\r\n")
                if line.lower().startswith(b"content-length:")
            )
            body = await reader.readexactly(length)
            request = httpx.Request("POST", "http://local/", content=body)
            payload = node.handle(request).content
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n"
                + f"Content-Length: {len(payload)}\r\n\r\n".encode()
                + payload
            )
            await writer.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    with socket.socket() as closed:
        closed.bind(("127.0.0.1", 0))
        dead = closed.getsockname()[1]  # 바인드 후 닫힘: 연결 거부
    primary = f"http://127.0.0.1:{dead}/v3/SECRETKEY1"
    fallback = f"http://127.0.0.1:{port}/v3/SECRETKEY2"
    caplog.set_level(logging.DEBUG)
    try:
        async with httpx.AsyncClient(timeout=4, trust_env=False) as client:
            rpc = FailoverWalletRpc(
                client,
                (primary, fallback),
                chain_id=31337,
                address=ADDRESS,
                deployment_block=1,
                deployment_hash=DEPLOYMENT_HASH,
                runtime_code_hash="0x" + keccak(CODE).hex(),
                abi=ABI,
            )
            response = await get_document(document_app(rpc))
            assert response.status_code == 404 and rpc.on_fallback
            server.close()
            await server.wait_closed()
            down = await get_document(document_app(rpc))
            assert down.status_code == 503
    finally:
        server.close()
    logs = everything_logged(caplog)
    assert "wallet RPC primary failed" in logs
    assert_no_secret(response.text, down.text, logs)
    for host in ("127.0.0.1", f":{dead}", f":{port}"):
        assert host not in logs, host
