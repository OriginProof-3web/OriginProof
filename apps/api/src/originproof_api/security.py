"""Bounded request protection for the single-worker local P0 API."""

import asyncio
import math
from time import monotonic

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse


class RequestSecurity:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        # ponytail: one local API worker; shared atomic counters before multiple workers/replicas.
        self.buckets = {}

    def allowance(self, peer, login):
        now = monotonic()
        self.buckets = {k: v for k, v in self.buckets.items() if now < v[0]}
        keys = [("api", peer, self.settings.requests_per_minute)]
        if login:
            keys.append(("login", peer, self.settings.logins_per_minute))
        new_keys = sum((kind, peer) not in self.buckets for kind, peer, _ in keys)
        if len(self.buckets) + new_keys > 4096:
            return 60
        for kind, peer, limit in keys:
            deadline, count = self.buckets.get((kind, peer), (now + 60, 0))
            if count >= limit:
                return max(1, math.ceil(deadline - now))
        for kind, peer, _ in keys:
            deadline, count = self.buckets.get((kind, peer), (now + 60, 0))
            self.buckets[kind, peer] = deadline, count + 1
        return 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(("/v1/", "/v2/")):
            return await self.app(scope, receive, send)

        async def protected_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                headers["X-Content-Type-Options"] = "nosniff"
            await send(message)

        async def reject(status, error, headers=None):
            await JSONResponse({"error": error}, status_code=status, headers=headers)(
                scope, receive, protected_send
            )

        headers = Headers(scope=scope)
        peer = scope.get("client") or ("unknown", 0)
        # Forwarded headers are caller-controlled unless a trusted proxy is configured.
        retry = self.allowance(peer[0], scope["path"] == "/v1/auth/login")
        if retry:
            return await reject(429, "RATE_LIMITED", {"Retry-After": str(retry)})
        if scope["method"] not in ("GET", "HEAD", "OPTIONS"):
            origin = headers.get("origin")
            if (origin is not None and origin not in self.settings.browser_origins) or (
                origin is None and headers.get("sec-fetch-site") == "cross-site"
            ):
                return await reject(403, "ORIGIN_FORBIDDEN")
        length = headers.get("content-length")
        if length is not None:
            if not length.isascii() or not length.isdecimal():
                return await reject(400, "INVALID_CONTENT_LENGTH")
            normalized = length.lstrip("0") or "0"
            if len(normalized) > 10 or int(normalized) > self.settings.request_body_max_bytes:
                return await reject(413, "REQUEST_TOO_LARGE")

        async def read_body():
            buffer = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return None
                chunk = message.get("body", b"")
                if len(buffer) + len(chunk) > self.settings.request_body_max_bytes:
                    raise OverflowError
                buffer.extend(chunk)
                if not message.get("more_body", False):
                    return bytes(buffer)

        try:
            body = await asyncio.wait_for(
                read_body(), timeout=self.settings.request_body_timeout_seconds
            )
        except OverflowError:
            return await reject(413, "REQUEST_TOO_LARGE")
        except TimeoutError:
            return await reject(408, "REQUEST_TIMEOUT")
        if body is None:
            return

        async def replay():
            nonlocal body
            if body is not None:
                message = {"type": "http.request", "body": body, "more_body": False}
                body = None
                return message
            return await receive()

        await self.app(scope, replay, protected_send)
