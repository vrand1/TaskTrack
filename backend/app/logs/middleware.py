import json
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.exceptions import AppError

SKIP_PATHS = frozenset({"/health", "/api/docs", "/api/openapi.json", "/api/redoc"})
SENSITIVE_BODY_PATHS = frozenset({"/auth/token", "/api/v1/auth/token"})


def _pick_location(exc: BaseException) -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    if not tb:
        return "unknown"
    for frame in reversed(tb):
        path = frame.filename.replace("\\", "/")
        if "/app/" in path or "/backend/" in path:
            return f"{Path(frame.filename).name}:{frame.lineno} ({frame.name})"
    last = tb[-1]
    return f"{Path(last.filename).name}:{last.lineno} ({last.name})"


async def _decode_body(request: Request) -> object | None:
    if request.url.path in SENSITIVE_BODY_PATHS:
        return "<redacted>"
    body_bytes = await request.body()
    if not body_bytes:
        return None
    try:
        body_text = body_bytes[:4096].decode("utf-8", errors="replace")
        if "application/json" in request.headers.get("content-type", ""):
            return json.loads(body_text)
        return body_text
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"<{len(body_bytes)} bytes>"


def register_logging_middleware(app: FastAPI) -> None:
    """HTTP-only middleware: BaseHTTPMiddleware breaks WebSocket (/api/v1/ws)."""

    @app.middleware("http")
    async def logging_middleware(request: Request, call_next) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        req_body = await _decode_body(request)
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            request_body=req_body,
        ).info(f"REQUEST: {request.method} {request.url.path}")

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except (AppError, StarletteHTTPException):
            raise
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            location = _pick_location(exc)
            logger.bind(
                request_id=request_id,
                location=location,
                duration_ms=round(duration_ms, 2),
            ).exception(f"CRASH: {type(exc).__name__}: {exc} at {location}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error",
                    },
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        log = logger.bind(
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        msg = (
            f"RESPONSE: {request.method} {request.url.path} "
            f"[{response.status_code}] {duration_ms:.2f}ms"
        )
        if 200 <= response.status_code < 300:
            log.success(msg)
        elif 400 <= response.status_code < 500:
            log.warning(msg)
        else:
            log.error(msg)

        response.headers["X-Request-ID"] = request_id
        return response
