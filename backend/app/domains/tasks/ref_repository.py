
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.tasks.models import TaskPriorityRef, TaskStatusRef
from app.domains.tasks.refs import PriorityRef, StatusRef


class TaskRefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_statuses(self) -> list[StatusRef]:
        result = await self._session.scalars(
            select(TaskStatusRef).order_by(TaskStatusRef.sort_order)
        )
        return [
            StatusRef(id=row.id, code=row.code, sort_order=row.sort_order)
            for row in result.all()
        ]

    async def load_priorities(self) -> list[PriorityRef]:
        result = await self._session.scalars(select(TaskPriorityRef).order_by(TaskPriorityRef.id))
        return [PriorityRef(id=row.id, code=row.code) for row in result.all()]
