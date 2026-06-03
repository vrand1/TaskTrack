import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.tasks.models import TaskComment
from app.domains.tasks.params.comment import TaskCommentListParams


class TaskCommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, comment: TaskComment) -> TaskComment:
        self._session.add(comment)
        await self._session.flush()
        return await self.get_by_id(comment.id)

    async def get_by_id(self, comment_id: uuid.UUID) -> TaskComment:
        result = await self._session.execute(
            select(TaskComment)
            .options(selectinload(TaskComment.author))
            .where(TaskComment.id == comment_id)
        )
        return result.scalar_one()

    async def list_for_task(self, params: TaskCommentListParams) -> tuple[list[TaskComment], int]:
        query = (
            select(TaskComment)
            .options(selectinload(TaskComment.author))
            .where(TaskComment.task_id == params.task_id)
        )
        count_query = (
            select(func.count())
            .select_from(TaskComment)
            .where(TaskComment.task_id == params.task_id)
        )
        order = (
            TaskComment.created_at.asc()
            if params.sort == "asc"
            else TaskComment.created_at.desc()
        )
        query = query.order_by(order).offset(params.offset).limit(params.page_size)
        total = await self._session.scalar(count_query) or 0
        result = await self._session.scalars(query)
        return list(result.all()), total
