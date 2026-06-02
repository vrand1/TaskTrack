from __future__ import annotations

from contextvars import ContextVar

import grpc
import jwt
from grpc.aio import ServerInterceptor

from app.core.exceptions import AppError
from app.domains.auth.dependencies import get_access_token_validator
from app.domains.auth.ports import AuthenticatedPrincipal

_principal_ctx: ContextVar[AuthenticatedPrincipal | None] = ContextVar(
    "grpc_authenticated_principal", default=None
)


def get_current_principal() -> AuthenticatedPrincipal | None:
    return _principal_ctx.get()


class AuthInterceptor(ServerInterceptor):
    def __init__(self, *, public_methods: set[str]) -> None:
        self._public_methods = public_methods
        self._validator = get_access_token_validator()

    async def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        if method in self._public_methods:
            return await continuation(handler_call_details)

        token: str | None = None
        for key, value in (handler_call_details.invocation_metadata or ()):
            if key.lower() == "authorization" and value.lower().startswith("bearer "):
                token = value[7:].strip()
                break

        if not token:
            return grpc.unary_unary_rpc_method_handler(
                _abort_unauthenticated("Отсутствует Bearer-токен")
            )

        try:
            principal = await self._validator.validate(token)
        except jwt.PyJWTError:
            return grpc.unary_unary_rpc_method_handler(
                _abort_unauthenticated("Недействительный или истекший токен")
            )
        except AppError as exc:
            return grpc.unary_unary_rpc_method_handler(_abort_unauthenticated(exc.message))

        original = await continuation(handler_call_details)
        if original is None or original.unary_unary is None:
            return original

        async def wrapped_unary_unary(request, context):
            token_ctx = _principal_ctx.set(principal)
            try:
                return await original.unary_unary(request, context)
            finally:
                _principal_ctx.reset(token_ctx)

        return grpc.unary_unary_rpc_method_handler(
            wrapped_unary_unary,
            request_deserializer=original.request_deserializer,
            response_serializer=original.response_serializer,
        )


def _abort_unauthenticated(message: str):
    async def handler(_, context):
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, message)

    return handler
