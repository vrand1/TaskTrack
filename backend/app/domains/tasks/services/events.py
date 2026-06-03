import uuid

from app.domains.tasks.models import Task
from app.domains.tasks.schemas import TaskRead
from app.domains.users.model import User
from app.realtime.contracts import (
    TaskCommentAddedPayload,
    TaskCreatedPayload,
    TaskDeletedPayload,
    TaskRestoredPayload,
    TaskStatusChangedPayload,
    TaskUpdatedPayload,
)
from app.realtime.manager import realtime_manager


async def publish_task_created(result: TaskRead, *, actor: User) -> None:
    await realtime_manager.publish_scoped(
        event="task_created",
        payload=TaskCreatedPayload(
            task_id=str(result.id),
            project_id=str(result.project_id),
            actor=actor.email,
            assignee=result.assignee,
            status=result.status,
            priority=result.priority,
            was_reopened=result.was_reopened,
        ).model_dump(),
        project_id=str(result.project_id),
        task_id=str(result.id),
    )


async def publish_task_updated(
    result: TaskRead,
    *,
    actor: User,
    changes: list[dict],
) -> None:
    await realtime_manager.publish_scoped(
        event="task_updated",
        payload=TaskUpdatedPayload(
            task_id=str(result.id),
            project_id=str(result.project_id),
            actor=actor.email,
            assignee=result.assignee,
            changes=changes,
        ).model_dump(),
        project_id=str(result.project_id),
        task_id=str(result.id),
    )


async def publish_task_status_changed(
    result: TaskRead,
    *,
    actor: User,
    old_status: str,
    new_status: str,
    reopened: bool,
) -> None:
    await realtime_manager.publish_scoped(
        event="task_status_changed",
        payload=TaskStatusChangedPayload(
            task_id=str(result.id),
            project_id=str(result.project_id),
            actor=actor.email,
            assignee=result.assignee,
            from_status=old_status,
            to_status=new_status,
            reopened=reopened,
        ).model_dump(),
        project_id=str(result.project_id),
        task_id=str(result.id),
    )


async def publish_task_deleted(task: Task, *, actor: User) -> None:
    await realtime_manager.publish_scoped(
        event="task_deleted",
        payload=TaskDeletedPayload(
            task_id=str(task.id),
            project_id=str(task.project_id),
            actor=actor.email,
        ).model_dump(),
        project_id=str(task.project_id),
        task_id=str(task.id),
    )


async def publish_task_restored(result: TaskRead, *, actor: User) -> None:
    await realtime_manager.publish_scoped(
        event="task_restored",
        payload=TaskRestoredPayload(
            task_id=str(result.id),
            project_id=str(result.project_id),
            actor=actor.email,
            assignee=result.assignee,
        ).model_dump(),
        project_id=str(result.project_id),
        task_id=str(result.id),
    )


async def publish_task_comment_added(
    task: Task,
    *,
    actor: User,
    comment_id: uuid.UUID,
    body: str,
) -> None:
    await realtime_manager.publish_scoped(
        event="task_comment_added",
        payload=TaskCommentAddedPayload(
            task_id=str(task.id),
            project_id=str(task.project_id),
            comment_id=str(comment_id),
            actor=actor.email,
            body=body,
        ).model_dump(),
        project_id=str(task.project_id),
        task_id=str(task.id),
    )
