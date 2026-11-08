"""HTTP API: POST /v1/sessions and GET /healthz."""

from __future__ import annotations

import json
import logging
import math
import time
import zlib
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gtfs_zone_wifi_ingest.ratelimit import RateLimiter
from gtfs_zone_wifi_ingest.schema import SessionSchemas

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Response

    from gtfs_zone_wifi_ingest.config import Settings
    from gtfs_zone_wifi_ingest.store import SessionStore

log = logging.getLogger("gtfs_zone_wifi_ingest")


class BodyError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


async def read_body(request: Request, limit: int) -> bytes:
    """The request body, gunzipped if sent with Content-Encoding: gzip.

    Both the sent and the decompressed size are capped at `limit`.
    """
    encoding = request.headers.get("content-encoding", "identity").strip().lower()
    if encoding not in ("identity", "gzip"):
        raise BodyError(415, f"unsupported Content-Encoding: {encoding}")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise BodyError(413, f"body over {limit} bytes")
    gz = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    out = bytearray()
    sent = 0
    try:
        async for chunk in request.stream():
            sent += len(chunk)
            if sent > limit:
                raise BodyError(413, f"body over {limit} bytes")
            if gz is None:
                out += chunk
            else:
                # Stops one byte past the limit, so a gzip bomb never expands.
                out += gz.decompress(chunk, limit + 1 - len(out))
            if len(out) > limit:
                raise BodyError(413, f"decompressed body over {limit} bytes")
        if gz is not None:
            out += gz.flush()
            if len(out) > limit:
                raise BodyError(413, f"decompressed body over {limit} bytes")
            if not gz.eof:
                raise BodyError(400, "truncated gzip body")
    except zlib.error as e:
        raise BodyError(400, "invalid gzip body") from e
    return bytes(out)


def create_app(settings: Settings, store: SessionStore) -> FastAPI:
    schemas = SessionSchemas(settings.schema_dir)
    limiter = RateLimiter(settings.rate_limit, settings.rate_window_s)
    app = FastAPI(title="wifi.gtfs.zone ingest", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Replaces the uvicorn access log, which includes the client address.
        start = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        session_id = getattr(request.state, "session_id", "-")
        log.info(
            "%s %s %d %.0fms session=%s",
            request.method,
            request.url.path,
            response.status_code,
            ms,
            session_id,
        )
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/sessions")
    async def post_session(request: Request) -> JSONResponse:
        address = request.client.host if request.client else "unknown"
        retry = limiter.hit(address)
        if retry is not None:
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(math.ceil(retry))},
            )
        try:
            body = await read_body(request, settings.max_body_bytes)
        except BodyError as e:
            return JSONResponse({"detail": e.detail}, status_code=e.status)
        try:
            session = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse({"detail": "body is not JSON"}, status_code=400)
        errors = schemas.errors(session)
        if errors:
            return JSONResponse(
                {"detail": "session does not match the schema", "errors": errors},
                status_code=422,
            )
        session_id = session["session_id"]
        request.state.session_id = session_id
        created = await store.put(session["schema_version"], session_id, body)
        return JSONResponse(
            {"session_id": session_id, "status": "created" if created else "exists"},
            status_code=201 if created else 200,
        )

    return app
