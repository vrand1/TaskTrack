import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.tasks.constants import (
    EVENT_COMMENT_ADDED,
    EVENT_CREATED,
    EVENT_DELETED,
    EVENT_RESTORED,
    EVENT_STATUS_CHANGED,
    EVENT_UPDATED,
)
from app.domains.tasks.history_params import TaskHistoryListParams
from app.domains.tasks.models import Task, TaskEvent
from app.domains.users.model import User


class TaskHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        task_id: uuid.UUID,
        actor_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> TaskEvent:
        event = TaskEvent(
            task_id=task_id,
            actor_id=actor_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_for_task(self, params: TaskHistoryListParams) -> tuple[list[TaskEvent], int]:
        query = (
            select(TaskEvent)
            .options(selectinload(TaskEvent.actor))
            .where(TaskEvent.task_id == params.task_id)
        )
        count_query = (
            select(func.count())
            .select_from(TaskEvent)
            .where(TaskEvent.task_id == params.task_id)
        )

        if params.event_type is not None:
            query = query.where(TaskEvent.event_type == params.event_type)
            count_query = count_query.where(TaskEvent.event_type == params.event_type)
        if params.actor is not None:
            query = query.join(TaskEvent.actor).where(User.email == params.actor)
            count_query = count_query.join(TaskEvent.actor).where(User.email == params.actor)
        if params.created_after is not None:
            query = query.where(TaskEvent.created_at >= params.created_after)
            count_query = count_query.where(TaskEvent.created_at >= params.created_after)
        if params.created_before is not None:
            query = query.where(TaskEvent.created_at <= params.created_before)
            count_query = count_query.where(TaskEvent.created_at <= params.created_before)

        order = TaskEvent.created_at.asc() if params.sort == "asc" else TaskEvent.created_at.desc()
        query = query.order_by(order)
        query = query.offset(params.offset).limit(params.page_size)

        total = await self._session.scalar(count_query) or 0
        result = await self._session.scalars(query)
        return list(result.all()), total


class TaskHistoryRecorder:
    def __init__(self, repository: TaskHistoryRepository) -> None:
        self._repository = repository

    async def created(self, task: Task, *, actor_id: int) -> None:
        await self._repository.record(
            task_id=task.id,
            actor_id=actor_id,
            event_type=EVENT_CREATED,
            payload={
                "title": task.title,
                "assignee_id": task.assignee_id,
                "project_id": str(task.project_id),
                "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
                "status_id": task.status_id,
                "priority_id": task.priority_id,
                "start_at": task.start_at.isoformat() if task.start_at else None,
                "end_at": task.end_at.isoformat() if task.end_at else None,
                "tags": [row.tag.name for row in task.tags],
            },
        )

    async def status_changed(
        self,
        task: Task,
        *,
        actor_id: int,
        from_status: str,
        to_status: str,
        reopened: bool = False,
    ) -> None:
        await self._repository.record(
            task_id=task.id,
            actor_id=actor_id,
            event_type=EVENT_STATUS_CHANGED,
            payload={"from": from_status, "to": to_status, "reopened": reopened},
        )

    async def updated(
        self,
        task: Task,
        *,
        actor_id: int,
        changes: list[dict[str, Any]],
    ) -> None:
        if not changes:
            return
        await self._repository.record(
            task_id=task.id,
            actor_id=actor_id,
            event_type=EVENT_UPDATED,
            payload={"changes": changes},
        )

    async def deleted(self, task: Task, *, actor_id: int) -> None:
        await self._repository.record(
            task_id=task.id,
            actor_id=actor_id,
            event_type=EVENT_DELETED,
            payload={},
        )

    async def restored(self, task: Task, *, actor_id: int) -> None:
        await self._repository.record(
            task_id=task.id,
            actor_id=actor_id,
            event_type=EVENT_RESTORED,
            payload={},
        )

    async def comment_added(
        self,
        *,
        task_id: uuid.UUID,
        comment_id: uuid.UUID,
        actor_id: int,
        body: str,
    ) -> None:
        preview = body if len(body) <= 200 else f"{body[:197]}..."
        await self._repository.record(
            task_id=task_id,
            actor_id=actor_id,
            event_type=EVENT_COMMENT_ADDED,
            payload={"comment_id": str(comment_id), "body_preview": preview},
        )

    async def list_for_task(self, params: TaskHistoryListParams) -> tuple[list[TaskEvent], int]:
        return await self._repository.list_for_task(params)
