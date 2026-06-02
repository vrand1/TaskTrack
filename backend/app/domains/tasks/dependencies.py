from typing import Annotated

from fastapi import Depends

from app.api.dependencies import SessionDep
from app.cache.redis_client import get_redis
from app.cache.task_list import TaskListCache
from app.domains.auth.dependencies import UserStoreDep
from app.domains.projects.repository import ProjectRepository
from app.domains.tasks.comment_repository import TaskCommentRepository
from app.domains.tasks.history import TaskHistoryRecorder, TaskHistoryRepository
from app.domains.tasks.refs import get_task_ref_registry
from app.domains.tasks.repository import TaskRepository
from app.domains.tasks.service import TaskService


def get_task_list_cache() -> TaskListCache:
    return TaskListCache(get_redis())


def get_task_service(
    session: SessionDep,
    cache: Annotated[TaskListCache, Depends(get_task_list_cache)],
    users: UserStoreDep,
) -> TaskService:
    history_repo = TaskHistoryRepository(session)
    refs = get_task_ref_registry()
    return TaskService(
        repository=TaskRepository(session, refs),
        projects=ProjectRepository(session),
        users=users,
        history=TaskHistoryRecorder(history_repo),
        comments=TaskCommentRepository(session),
        cache=cache,
        refs=refs,
    )


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
