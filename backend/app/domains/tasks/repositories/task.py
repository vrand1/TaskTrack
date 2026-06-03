import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.config import settings
from app.core.datetime_utils import ensure_utc
from app.core.exceptions import RestoreExpiredError, TaskNotFoundError
from app.domains.projects.model import Project
from app.domains.tasks.domain.refs import TaskRefRegistry
from app.domains.tasks.models import Tag, Task, TaskTag
from app.domains.tasks.params.list import TaskListParams
from app.domains.tasks.params.tag_list import TagListParams
from app.domains.users.model import User

TASK_LOAD = (
    selectinload(Task.assignee_user),
    selectinload(Task.project),
    selectinload(Task.tags).selectinload(TaskTag.tag),
)

_SORT_COLUMNS = {
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "title": Task.title,
    "start_at": Task.start_at,
    "end_at": Task.end_at,
}


class TaskRepository:
    def __init__(self, session: AsyncSession, refs: TaskRefRegistry) -> None:
        self._session = session
        self._refs = refs

    async def add(self, task: Task) -> Task:
        self._session.add(task)
        await self._session.flush()
        return await self.get_active_by_id(task.id)

    async def get_active_by_id(self, task_id: uuid.UUID) -> Task:
        result = await self._session.execute(
            select(Task)
            .options(*TASK_LOAD)
            .where(Task.id == task_id, Task.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return task

    def _apply_list_filters(self, params: TaskListParams):
        query = select(Task).options(*TASK_LOAD).where(Task.deleted_at.is_(None))
        count_query = select(func.count()).select_from(Task).where(Task.deleted_at.is_(None))

        if params.project_id is not None:
            query = query.where(Task.project_id == params.project_id)
            count_query = count_query.where(Task.project_id == params.project_id)
        if params.parent_task_id is not None:
            query = query.where(Task.parent_task_id == params.parent_task_id)
            count_query = count_query.where(Task.parent_task_id == params.parent_task_id)
        elif params.root_only:
            query = query.where(Task.parent_task_id.is_(None))
            count_query = count_query.where(Task.parent_task_id.is_(None))

        if params.status is not None:
            status_id = self._refs.status_id(params.status)
            query = query.where(Task.status_id == status_id)
            count_query = count_query.where(Task.status_id == status_id)
        if params.priority is not None:
            priority_id = self._refs.priority_id(params.priority)
            query = query.where(Task.priority_id == priority_id)
            count_query = count_query.where(Task.priority_id == priority_id)
        if params.assignee is not None:
            query = query.join(Task.assignee_user).where(User.email == params.assignee)
            count_query = count_query.join(Task.assignee_user).where(
                User.email == params.assignee
            )
        if params.q:
            escaped = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            query = query.where(Task.title.ilike(pattern, escape="\\"))
            count_query = count_query.where(Task.title.ilike(pattern, escape="\\"))
        if params.tag is not None:
            tag_subquery = (
                select(TaskTag.task_id)
                .join(Tag, TaskTag.tag_id == Tag.id)
                .where(Tag.name == params.tag)
            )
            query = query.where(
                Task.id.in_(tag_subquery)
            )
            count_query = count_query.where(
                Task.id.in_(tag_subquery)
            )

        if params.leaves_only:
            child = aliased(Task)
            has_children = (
                select(1)
                .where(
                    child.parent_task_id == Task.id,
                    child.deleted_at.is_(None),
                )
                .correlate(Task)
                .exists()
            )
            query = query.where(~has_children)
            count_query = count_query.where(~has_children)

        return query, count_query

    async def list_active(self, params: TaskListParams) -> tuple[list[Task], int]:
        query, count_query = self._apply_list_filters(params)
        sort_column = _SORT_COLUMNS.get(params.sort_by, Task.created_at)
        order = sort_column.asc() if params.sort_order == "asc" else sort_column.desc()
        if params.sort_by in {"start_at", "end_at"}:
            order = order.nulls_last() if params.sort_order == "asc" else order.nulls_first()
        query = query.order_by(order).offset(params.offset).limit(params.page_size)

        total = await self._session.scalar(count_query) or 0
        result = await self._session.scalars(query)
        return list(result.all()), total

    async def list_children(self, parent_task_id: uuid.UUID) -> list[Task]:
        params = TaskListParams(
            parent_task_id=parent_task_id,
            page_size=settings.tasks_max_page_size,
        )
        tasks, _ = await self.list_active(params)
        return tasks

    async def list_tags(self, params: TagListParams) -> tuple[list[Tag], int]:
        query = select(Tag)
        count_query = select(func.count()).select_from(Tag)

        if params.q:
            escaped = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            query = query.where(Tag.name.ilike(pattern, escape="\\"))
            count_query = count_query.where(Tag.name.ilike(pattern, escape="\\"))

        if params.project_id is not None:
            tag_ids = (
                select(Tag.id)
                .join(TaskTag, TaskTag.tag_id == Tag.id)
                .join(Task, Task.id == TaskTag.task_id)
                .where(
                    Task.project_id == params.project_id,
                    Task.deleted_at.is_(None),
                )
                .distinct()
            )
            query = query.where(Tag.id.in_(tag_ids))
            count_query = count_query.where(Tag.id.in_(tag_ids))

        query = query.order_by(Tag.name.asc()).offset(params.offset).limit(params.page_size)

        total = await self._session.scalar(count_query) or 0
        result = await self._session.scalars(query)
        return list(result.all()), total

    async def save(self, task: Task) -> Task:
        task.updated_at = datetime.now(UTC)
        await self._session.flush()
        return await self.get_active_by_id(task.id)

    async def set_tags(self, task: Task, tags: list[str]) -> None:
        unique_tag_names = sorted(set(tags))

        task.tags.clear()
        await self._session.flush()

        if not unique_tag_names:
            return

        existing_tags = await self._session.scalars(
            select(Tag).where(Tag.name.in_(unique_tag_names))
        )
        tag_by_name = {row.name: row for row in existing_tags}

        missing = [name for name in unique_tag_names if name not in tag_by_name]
        if missing:
            self._session.add_all([Tag(name=name) for name in missing])
            await self._session.flush()

        existing_tags = await self._session.scalars(
            select(Tag).where(Tag.name.in_(unique_tag_names))
        )
        tag_by_name = {row.name: row for row in existing_tags}

        for name in unique_tag_names:
            self._session.add(TaskTag(task_id=task.id, tag_id=tag_by_name[name].id))
        await self._session.flush()

    async def soft_delete(self, task: Task) -> None:
        task.deleted_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def get_restorable(self, task_id: uuid.UUID) -> Task:
        result = await self._session.execute(
            select(Task).options(*TASK_LOAD).where(Task.id == task_id, Task.deleted_at.is_not(None))
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise TaskNotFoundError(str(task_id))

        cutoff = datetime.now(UTC) - timedelta(days=settings.soft_delete_retention_days)
        if ensure_utc(task.deleted_at) < cutoff:
            raise RestoreExpiredError(
                entity="Task",
                retention_days=settings.soft_delete_retention_days,
            )
        return task

    async def restore(self, task: Task) -> Task:
        task.deleted_at = None
        task.updated_at = datetime.now(UTC)
        await self._session.flush()
        return await self.get_active_by_id(task.id)

    async def project_exists(self, project_id: uuid.UUID) -> bool:
        count = await self._session.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        return bool(count)
