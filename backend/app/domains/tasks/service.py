import uuid
from typing import Any

from app.cache.task_list import TaskListCache
from app.core.exceptions import (
    InvalidParentTaskError,
    TaskAlreadyReopenedError,
    TaskNotFoundError,
    TaskNotReopenableError,
)
from app.domains.projects.repository import ProjectRepository
from app.domains.tasks.comment_params import TaskCommentListParams
from app.domains.tasks.comment_repository import TaskCommentRepository
from app.domains.tasks.constants import DEFAULT_TASK_STATUS
from app.domains.tasks.fsm import validate_status_transition
from app.domains.tasks.history import TaskHistoryRecorder
from app.domains.tasks.history_params import TaskHistoryListParams
from app.domains.tasks.list_params import TaskListParams
from app.domains.tasks.models import Task, TaskComment
from app.domains.tasks.refs import TaskRefRegistry
from app.domains.tasks.repository import TaskRepository
from app.domains.tasks.schemas import (
    TaskCommentCreate,
    TaskCommentListResponse,
    TaskCommentRead,
    TaskCreate,
    TaskHistoryEntry,
    TaskHistoryResponse,
    TaskListResponse,
    TaskRead,
    TaskUpdate,
)
from app.domains.users.model import User
from app.domains.users.ports import UserStore
from app.realtime.contracts import (
    TaskCommentAddedPayload,
    TaskCreatedPayload,
    TaskDeletedPayload,
    TaskRestoredPayload,
    TaskStatusChangedPayload,
    TaskUpdatedPayload,
)
from app.realtime.manager import realtime_manager


class TaskService:
    def __init__(
        self,
        repository: TaskRepository,
        projects: ProjectRepository,
        users: UserStore,
        history: TaskHistoryRecorder,
        comments: TaskCommentRepository,
        cache: TaskListCache,
        refs: TaskRefRegistry,
    ) -> None:
        self._repository = repository
        self._projects = projects
        self._users = users
        self._history = history
        self._comments = comments
        self._cache = cache
        self._refs = refs

    async def create(self, data: TaskCreate, *, actor: User) -> TaskRead:
        await self._projects.get_active_by_id(data.project_id)
        await self._validate_parent(
            project_id=data.project_id,
            parent_task_id=data.parent_task_id,
        )

        assignee = await self._users.require_active_by_email(data.assignee)

        task = Task(
            project_id=data.project_id,
            parent_task_id=data.parent_task_id,
            title=data.title,
            description=data.description,
            assignee_id=assignee.id,
            status_id=self._refs.status_id(DEFAULT_TASK_STATUS),
            priority_id=self._refs.priority_id(data.priority),
            start_at=data.start_at,
            end_at=data.end_at,
        )
        created = await self._repository.add(task)
        if data.tags:
            await self._repository.set_tags(created, data.tags)
            created = await self._repository.get_active_by_id(created.id)
        await self._history.created(created, actor_id=actor.id)
        await self._cache.invalidate_all()
        result = TaskRead.from_db(created, refs=self._refs)
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
        return result

    async def get_by_id(
        self,
        task_id: uuid.UUID,
        *,
        include_subtasks: bool = False,
    ) -> TaskRead:
        task = await self._repository.get_active_by_id(task_id)
        subtasks = await self._build_subtask_tree(task.id) if include_subtasks else None
        return TaskRead.from_db(task, refs=self._refs, subtasks=subtasks)

    async def list_subtasks(self, task_id: uuid.UUID) -> TaskListResponse:
        await self._repository.get_active_by_id(task_id)
        tasks = await self._repository.list_children(task_id)
        return TaskListResponse.build(
            items=[TaskRead.from_db(task, refs=self._refs) for task in tasks],
            total=len(tasks),
            page=1,
            page_size=max(len(tasks), 1),
        )

    async def add_comment(
        self,
        task_id: uuid.UUID,
        data: TaskCommentCreate,
        *,
        actor: User,
    ) -> TaskCommentRead:
        task = await self._repository.get_active_by_id(task_id)
        comment = TaskComment(
            task_id=task_id,
            author_id=actor.id,
            body=data.body,
        )
        saved = await self._comments.add(comment)
        await self._history.comment_added(
            task_id=task_id,
            comment_id=saved.id,
            actor_id=actor.id,
            body=saved.body,
        )
        await self._cache.invalidate_all()
        comment = TaskCommentRead.from_db(saved)
        await realtime_manager.publish_scoped(
            event="task_comment_added",
            payload=TaskCommentAddedPayload(
                task_id=str(task_id),
                project_id=str(task.project_id),
                comment_id=str(saved.id),
                actor=actor.email,
                body=saved.body,
            ).model_dump(),
            project_id=str(task.project_id),
            task_id=str(task_id),
        )
        return comment

    async def list_comments(self, params: TaskCommentListParams) -> TaskCommentListResponse:
        await self._repository.get_active_by_id(params.task_id)
        comments, total = await self._comments.list_for_task(params)
        return TaskCommentListResponse.build(
            items=[TaskCommentRead.from_db(item) for item in comments],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def list_history(self, params: TaskHistoryListParams) -> TaskHistoryResponse:
        await self._repository.get_active_by_id(params.task_id)
        events, total = await self._history.list_for_task(params)
        return TaskHistoryResponse.build(
            items=[TaskHistoryEntry.from_db(event) for event in events],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def list_tasks(self, params: TaskListParams) -> TaskListResponse:
        cached = await self._cache.get(params)
        if cached is not None:
            return cached

        tasks, total = await self._repository.list_active(params)
        response = TaskListResponse.build(
            items=[TaskRead.from_db(task, refs=self._refs) for task in tasks],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )
        await self._cache.set(params, response)
        return response

    async def update(self, task_id: uuid.UUID, data: TaskUpdate, *, actor: User) -> TaskRead:
        task = await self._repository.get_active_by_id(task_id)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return TaskRead.from_db(task, refs=self._refs)

        changes: list[dict[str, Any]] = []

        if "parent_task_id" in updates:
            new_parent_id = updates.pop("parent_task_id")
            await self._validate_parent(
                project_id=task.project_id,
                parent_task_id=new_parent_id,
                task_id=task.id,
            )
            if task.parent_task_id != new_parent_id:
                changes.append(
                    {
                        "field": "parent_task_id",
                        "old": str(task.parent_task_id) if task.parent_task_id else None,
                        "new": str(new_parent_id) if new_parent_id else None,
                    }
                )
                task.parent_task_id = new_parent_id

        if "assignee" in updates:
            assignee = await self._users.require_active_by_email(updates.pop("assignee"))
            if task.assignee_id != assignee.id:
                changes.append(
                    {
                        "field": "assignee",
                        "old": task.assignee_user.email,
                        "new": assignee.email,
                    }
                )
                task.assignee_id = assignee.id

        if "priority" in updates:
            priority_code = updates.pop("priority")
            new_priority_id = self._refs.priority_id(priority_code)
            if task.priority_id != new_priority_id:
                changes.append(
                    {
                        "field": "priority",
                        "old": self._refs.priority_code(task.priority_id),
                        "new": priority_code,
                    }
                )
                task.priority_id = new_priority_id

        if "tags" in updates:
            new_tags = updates.pop("tags")
            old_tags = sorted(row.tag.name for row in task.tags)
            if old_tags != new_tags:
                changes.append({"field": "tags", "old": old_tags, "new": new_tags})
                await self._repository.set_tags(task, new_tags)

        for field, value in updates.items():
            old_value = getattr(task, field)
            if old_value != value:
                changes.append({"field": field, "old": old_value, "new": value})
            setattr(task, field, value)

        saved = await self._repository.save(task)
        await self._history.updated(saved, actor_id=actor.id, changes=changes)
        await self._cache.invalidate_all()
        result = TaskRead.from_db(saved, refs=self._refs)
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
        return result

    async def update_status(self, task_id: uuid.UUID, status_code: str, *, actor: User) -> TaskRead:
        task = await self._repository.get_active_by_id(task_id)
        old_status = self._refs.status_code(task.status_id)
        validate_status_transition(
            old_status,
            status_code,
            ordered_codes=self._refs.ordered_status_codes(),
        )

        task.status_id = self._refs.status_id(status_code)
        saved = await self._repository.save(task)
        return await self._after_status_change(
            saved,
            actor=actor,
            old_status=old_status,
            new_status=status_code,
            reopened=False,
        )

    async def reopen(self, task_id: uuid.UUID, *, actor: User) -> TaskRead:
        task = await self._repository.get_active_by_id(task_id)
        old_status = self._refs.status_code(task.status_id)
        terminal_status = self._refs.terminal_status_code()
        if old_status != terminal_status:
            raise TaskNotReopenableError(
                current_status=old_status,
                terminal_status=terminal_status,
            )
        if task.was_reopened:
            raise TaskAlreadyReopenedError()

        new_status = self._refs.ordered_status_codes()[0]
        task.status_id = self._refs.status_id(new_status)
        task.was_reopened = True
        saved = await self._repository.save(task)
        return await self._after_status_change(
            saved,
            actor=actor,
            old_status=old_status,
            new_status=new_status,
            reopened=True,
        )

    async def _after_status_change(
        self,
        task: Task,
        *,
        actor: User,
        old_status: str,
        new_status: str,
        reopened: bool,
    ) -> TaskRead:
        await self._history.status_changed(
            task,
            actor_id=actor.id,
            from_status=old_status,
            to_status=new_status,
            reopened=reopened,
        )
        await self._cache.invalidate_all()
        result = TaskRead.from_db(task, refs=self._refs)
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
        return result

    async def delete(self, task_id: uuid.UUID, *, actor: User) -> None:
        task = await self._repository.get_active_by_id(task_id)
        await self._history.deleted(task, actor_id=actor.id)
        await self._repository.soft_delete(task)
        await self._cache.invalidate_all()
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

    async def restore(self, task_id: uuid.UUID, *, actor: User) -> TaskRead:
        task = await self._repository.get_restorable(task_id)
        restored = await self._repository.restore(task)
        await self._history.restored(restored, actor_id=actor.id)
        await self._cache.invalidate_all()
        result = TaskRead.from_db(restored, refs=self._refs)
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
        return result

    async def _build_subtask_tree(self, parent_id: uuid.UUID) -> list[TaskRead]:
        children = await self._repository.list_children(parent_id)
        result: list[TaskRead] = []
        for child in children:
            nested = await self._build_subtask_tree(child.id)
            result.append(TaskRead.from_db(child, refs=self._refs, subtasks=nested or None))
        return result

    async def _validate_parent(
        self,
        *,
        project_id: uuid.UUID,
        parent_task_id: uuid.UUID | None,
        task_id: uuid.UUID | None = None,
    ) -> None:
        if parent_task_id is None:
            return
        if task_id is not None and parent_task_id == task_id:
            raise InvalidParentTaskError("Задача не может быть родителем самой себя")

        try:
            parent = await self._repository.get_active_by_id(parent_task_id)
        except TaskNotFoundError as exc:
            raise InvalidParentTaskError(
                f"Родительская задача {parent_task_id} не найдена"
            ) from exc

        if parent.project_id != project_id:
            raise InvalidParentTaskError("Родительская задача должна принадлежать тому же проекту")

        if task_id is not None:
            await self._ensure_not_descendant(task_id, parent_task_id)

    async def _ensure_not_descendant(self, task_id: uuid.UUID, new_parent_id: uuid.UUID) -> None:
        current_id: uuid.UUID | None = new_parent_id
        while current_id is not None:
            if current_id == task_id:
                raise InvalidParentTaskError(
                    "Нельзя назначить родителя: возникнет цикл в дереве задач"
                )
            parent_task = await self._repository.get_active_by_id(current_id)
            current_id = parent_task.parent_task_id
