from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotency.model import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> IdempotencyKey | None:
        return await self._session.get(IdempotencyKey, key)

    async def save(
        self,
        *,
        key: str,
        scope: str,
        request_hash: str,
        status_code: int,
        response_body: str,
    ) -> None:
        self._session.add(
            IdempotencyKey(
                key=key,
                scope=scope,
                request_hash=request_hash,
                status_code=status_code,
                response_body=response_body,
            )
        )
        await self._session.flush()
