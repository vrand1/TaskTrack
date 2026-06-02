from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _validation_error_details(exc: RequestValidationError) -> list[dict]:
    sanitized: list[dict] = []
    for err in exc.errors():
        item = dict(err)
        ctx = item.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {key: str(value) for key, value in ctx.items()}
        sanitized.append(item)
    return sanitized


def _error_payload(exc: AppError, request_id: str | None) -> dict:
    payload: dict = {"error": {"code": exc.code, "message": exc.message}}
    if request_id is not None:
        payload["request_id"] = request_id
    return payload


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = _request_id(request)
        log = logger.bind(request_id=request_id, error_code=exc.code)
        log_msg = f"{exc.code}: {exc.message}"
        if exc.status_code >= 500:
            log.error(log_msg)
        else:
            log.warning(log_msg)

        headers = {"X-Request-ID": request_id} if request_id else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc, request_id),
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        request_id = _request_id(request)
        logger.bind(request_id=request_id).warning(
            "HTTP {}: {}", exc.status_code, exc.detail
        )
        content: dict = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            },
        }
        if request_id is not None:
            content["request_id"] = request_id
        headers = {"X-Request-ID": request_id} if request_id else None
        return JSONResponse(status_code=exc.status_code, content=content, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = _request_id(request)
        logger.bind(request_id=request_id).warning("Validation failed")
        details = _validation_error_details(exc)
        message = "; ".join(
            f"{'.'.join(str(part) for part in err.get('loc', ()))}: {err.get('msg', 'invalid')}"
            for err in details
        )
        content: dict = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message or "Request validation failed",
                "details": details,
            },
        }
        if request_id is not None:
            content["request_id"] = request_id
        headers = {"X-Request-ID": request_id} if request_id else None
        return JSONResponse(status_code=422, content=content, headers=headers)
