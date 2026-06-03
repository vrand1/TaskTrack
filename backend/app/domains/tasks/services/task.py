import uuid

from app.cache.task_list import TaskListCache
from app.core.exceptions import TaskAlreadyReopenedError, TaskNotReopenableError
from app.domains.projects.repository import ProjectRepository
from app.domains.tasks.domain.constants import DEFAULT_TASK_STATUS
from app.domains.tasks.domain.fsm import validate_status_transition
from app.domains.tasks.domain.history import TaskHistoryRecorder
from app.domains.tasks.domain.refs import TaskRefRegistry
from app.domains.tasks.models import Task, TaskComment
from app.domains.tasks.params.comment import TaskCommentListParams
from app.domains.tasks.params.history import TaskHistoryListParams
from app.domains.tasks.params.list import TaskListParams
from app.domains.tasks.params.tag_list import TagListParams
from app.domains.tasks.repositories.comment import TaskCommentRepository
from app.domains.tasks.repositories.task import TaskRepository
from app.domains.tasks.schemas import (
    TagListResponse,
    TagRead,
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
from app.domains.tasks.services import events as task_events
from app.domains.tasks.services.parent_rules import ParentTaskRules
from app.domains.tasks.services.update_apply import apply_task_update
from app.domains.users.model import User
from app.domains.users.ports import UserStore


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
        self._parent_rules = ParentTaskRules(repository, refs)

    async def create(self, data: TaskCreate, *, actor: User) -> TaskRead:
        await self._projects.get_active_by_id(data.project_id)
        await self._parent_rules.validate_parent(
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
        await task_events.publish_task_created(result, actor=actor)
        return result

    async def get_by_id(
        self,
        task_id: uuid.UUID,
        *,
        include_subtasks: bool = False,
    ) -> TaskRead:
        task = await self._repository.get_active_by_id(task_id)
        subtasks = (
            await self._parent_rules.build_subtask_tree(task.id) if include_subtasks else None
        )
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
        await task_events.publish_task_comment_added(
            task,
            actor=actor,
            comment_id=saved.id,
            body=saved.body,
        )
        return TaskCommentRead.from_db(saved)

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
        events_list, total = await self._history.list_for_task(params)
        return TaskHistoryResponse.build(
            items=[TaskHistoryEntry.from_db(event) for event in events_list],
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

    async def list_tags(self, params: TagListParams) -> TagListResponse:
        if params.project_id is not None:
            await self._projects.get_active_by_id(params.project_id)

        tags, total = await self._repository.list_tags(params)
        return TagListResponse.build(
            items=[TagRead.from_db(tag) for tag in tags],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def update(self, task_id: uuid.UUID, data: TaskUpdate, *, actor: User) -> TaskRead:
        task = await self._repository.get_active_by_id(task_id)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return TaskRead.from_db(task, refs=self._refs)

        changes = await apply_task_update(
            task,
            updates,
            repository=self._repository,
            users=self._users,
            refs=self._refs,
            parent_rules=self._parent_rules,
        )

        saved = await self._repository.save(task)
        await self._history.updated(saved, actor_id=actor.id, changes=changes)
        await self._cache.invalidate_all()
        result = TaskRead.from_db(saved, refs=self._refs)
        await task_events.publish_task_updated(result, actor=actor, changes=changes)
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

    async def delete(self, task_id: uuid.UUID, *, actor: User) -> None:
        task = await self._repository.get_active_by_id(task_id)
        await self._history.deleted(task, actor_id=actor.id)
        await self._repository.soft_delete(task)
        await self._cache.invalidate_all()
        await task_events.publish_task_deleted(task, actor=actor)

    async def restore(self, task_id: uuid.UUID, *, actor: User) -> TaskRead:
        task = await self._repository.get_restorable(task_id)
        restored = await self._repository.restore(task)
        await self._history.restored(restored, actor_id=actor.id)
        await self._cache.invalidate_all()
        result = TaskRead.from_db(restored, refs=self._refs)
        await task_events.publish_task_restored(result, actor=actor)
        return result

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
        await task_events.publish_task_status_changed(
            result,
            actor=actor,
            old_status=old_status,
            new_status=new_status,
            reopened=reopened,
        )
        return result
