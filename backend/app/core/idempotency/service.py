import hashlib
import json
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from app.core.exceptions import IdempotencyConflictError
from app.core.idempotency.repository import IdempotencyRepository


def request_body_hash(payload: BaseModel) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class IdempotencyService:
    def __init__(self, repository: IdempotencyRepository) -> None:
        self._repository = repository

    async def run(
        self,
        *,
        key: str | None,
        scope: str,
        request_hash: str,
        handler: Callable[[], Awaitable[BaseModel]],
        status_code: int,
        response_type: type[BaseModel],
    ) -> BaseModel:
        if key is None:
            return await handler()

        existing = await self._repository.get(key)
        if existing is not None:
            if existing.scope != scope or existing.request_hash != request_hash:
                raise IdempotencyConflictError()
            return response_type.model_validate_json(existing.response_body)

        result = await handler()
        await self._repository.save(
            key=key,
            scope=scope,
            request_hash=request_hash,
            status_code=status_code,
            response_body=result.model_dump_json(),
        )
        return result
