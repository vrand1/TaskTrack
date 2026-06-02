from typing import Annotated

from fastapi import Depends

from app.api.dependencies import SessionDep
from app.core.idempotency.repository import IdempotencyRepository
from app.core.idempotency.service import IdempotencyService


def get_idempotency_service(session: SessionDep) -> IdempotencyService:
    return IdempotencyService(IdempotencyRepository(session))


IdempotencyServiceDep = Annotated[IdempotencyService, Depends(get_idempotency_service)]
