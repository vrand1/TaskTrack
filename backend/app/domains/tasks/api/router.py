import uuid
from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.idempotency import IdempotencyServiceDep, request_body_hash
from app.domains.auth.dependencies import CurrentUserDep
from app.domains.tasks.api.dependencies import TaskServiceDep
from app.domains.tasks.params.comment import TaskCommentListParams
from app.domains.tasks.params.history import TaskHistoryListParams
from app.domains.tasks.params.list import TaskListParams
from app.domains.tasks.schemas import (
    TaskCommentCreate,
    TaskCommentFilterParams,
    TaskCommentListResponse,
    TaskCommentRead,
    TaskCreate,
    TaskFilterParams,
    TaskHistoryFilterParams,
    TaskHistoryResponse,
    TaskListResponse,
    TaskPaginationParams,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

IdempotencyKeyHeader = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        max_length=128,
        description="Ключ идемпотентности для дедупликации повторных POST-запросов.",
    ),
]


def list_query_params(
    filters: Annotated[TaskFilterParams, Depends()],
    pagination: Annotated[TaskPaginationParams, Depends()],
) -> TaskListParams:
    return filters.to_list_params(pagination)


def history_query_params(
    task_id: uuid.UUID,
    filters: Annotated[TaskHistoryFilterParams, Depends()],
    pagination: Annotated[TaskPaginationParams, Depends()],
) -> TaskHistoryListParams:
    return filters.to_list_params(task_id, pagination)


def comment_query_params(
    task_id: uuid.UUID,
    filters: Annotated[TaskCommentFilterParams, Depends()],
    pagination: Annotated[TaskPaginationParams, Depends()],
) -> TaskCommentListParams:
    return filters.to_list_params(task_id, pagination)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    service: TaskServiceDep,
    actor: CurrentUserDep,
    idempotency: IdempotencyServiceDep,
    idempotency_key: IdempotencyKeyHeader = None,
) -> TaskRead:
    result = await idempotency.run(
        key=idempotency_key,
        scope="POST /tasks",
        request_hash=request_body_hash(data),
        handler=lambda: service.create(data, actor=actor),
        status_code=status.HTTP_201_CREATED,
        response_type=TaskRead,
    )
    return result  # type: ignore[return-value]


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    service: TaskServiceDep,
    _: CurrentUserDep,
    params: Annotated[TaskListParams, Depends(list_query_params)],
) -> TaskListResponse:
    return await service.list_tasks(params)


@router.get("/me", response_model=TaskListResponse)
async def list_my_tasks(
    service: TaskServiceDep,
    actor: CurrentUserDep,
    params: Annotated[TaskListParams, Depends(list_query_params)],
) -> TaskListResponse:
    return await service.list_tasks(replace(params, assignee=actor.email))


@router.get("/me/leaves", response_model=TaskListResponse)
async def list_my_leaf_tasks(
    service: TaskServiceDep,
    actor: CurrentUserDep,
    params: Annotated[TaskListParams, Depends(list_query_params)],
) -> TaskListResponse:
    return await service.list_tasks(
        replace(params, assignee=actor.email, leaves_only=True)
    )


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    service: TaskServiceDep,
    _: CurrentUserDep,
    include_subtasks: Annotated[
        bool, Query(description="Если true, вернуть рекурсивное дерево подзадач.")
    ] = False,
) -> TaskRead:
    return await service.get_by_id(task_id, include_subtasks=include_subtasks)


@router.get("/{task_id}/subtasks", response_model=TaskListResponse)
async def list_subtasks(
    task_id: uuid.UUID,
    service: TaskServiceDep,
    _: CurrentUserDep,
) -> TaskListResponse:
    return await service.list_subtasks(task_id)


@router.get("/{task_id}/history", response_model=TaskHistoryResponse)
async def list_task_history(
    service: TaskServiceDep,
    _: CurrentUserDep,
    params: Annotated[TaskHistoryListParams, Depends(history_query_params)],
) -> TaskHistoryResponse:
    return await service.list_history(params)


@router.get("/{task_id}/comments", response_model=TaskCommentListResponse)
async def list_task_comments(
    service: TaskServiceDep,
    _: CurrentUserDep,
    params: Annotated[TaskCommentListParams, Depends(comment_query_params)],
) -> TaskCommentListResponse:
    return await service.list_comments(params)


@router.post(
    "/{task_id}/comments",
    response_model=TaskCommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_comment(
    task_id: uuid.UUID,
    data: TaskCommentCreate,
    service: TaskServiceDep,
    actor: CurrentUserDep,
    idempotency: IdempotencyServiceDep,
    idempotency_key: IdempotencyKeyHeader = None,
) -> TaskCommentRead:
    result = await idempotency.run(
        key=idempotency_key,
        scope=f"POST /tasks/{task_id}/comments",
        request_hash=request_body_hash(data),
        handler=lambda: service.add_comment(task_id, data, actor=actor),
        status_code=status.HTTP_201_CREATED,
        response_type=TaskCommentRead,
    )
    return result  # type: ignore[return-value]


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    service: TaskServiceDep,
    actor: CurrentUserDep,
) -> TaskRead:
    return await service.update(task_id, data, actor=actor)


@router.patch("/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: uuid.UUID,
    data: TaskStatusUpdate,
    service: TaskServiceDep,
    actor: CurrentUserDep,
) -> TaskRead:
    return await service.update_status(task_id, data.status, actor=actor)


@router.post("/{task_id}/reopen", response_model=TaskRead)
async def reopen_task(
    task_id: uuid.UUID,
    service: TaskServiceDep,
    actor: CurrentUserDep,
) -> TaskRead:
    return await service.reopen(task_id, actor=actor)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    service: TaskServiceDep,
    actor: CurrentUserDep,
) -> Response:
    await service.delete(task_id, actor=actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/restore", response_model=TaskRead)
async def restore_task(
    task_id: uuid.UUID,
    service: TaskServiceDep,
    actor: CurrentUserDep,
) -> TaskRead:
    return await service.restore(task_id, actor=actor)
