from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import grpc
from google.protobuf.empty_pb2 import Empty

from app.cache.redis_client import get_redis
from app.cache.task_list import TaskListCache
from app.core.exceptions import AppError, ForbiddenError
from app.db.session import async_session_factory
from app.domains.auth.providers.factory import build_user_store
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.service import ProjectService
from app.domains.tasks.comment_repository import TaskCommentRepository
from app.domains.tasks.history import TaskHistoryRecorder, TaskHistoryRepository
from app.domains.tasks.list_params import TaskListParams
from app.domains.tasks.refs import get_task_ref_registry
from app.domains.tasks.repository import TaskRepository
from app.domains.tasks.schemas import TaskCreate
from app.domains.tasks.service import TaskService

from . import auth
from .generated import task_service_pb2 as pb2
from .generated import task_service_pb2_grpc as pb2_grpc
from .mappers import to_proto_project, to_proto_task

_APP_TO_GRPC_STATUS = {
    400: grpc.StatusCode.INVALID_ARGUMENT,
    401: grpc.StatusCode.UNAUTHENTICATED,
    403: grpc.StatusCode.PERMISSION_DENIED,
    404: grpc.StatusCode.NOT_FOUND,
    409: grpc.StatusCode.ALREADY_EXISTS,
    410: grpc.StatusCode.FAILED_PRECONDITION,
    422: grpc.StatusCode.INVALID_ARGUMENT,
    501: grpc.StatusCode.UNIMPLEMENTED,
}


@asynccontextmanager
async def _session_scope():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _require_actor(*, context: grpc.aio.ServicerContext, require_admin: bool = False):
    principal = auth.get_current_principal()
    if principal is None:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Требуется аутентификация")

    async with _session_scope() as session:
        store = build_user_store(session)
        actor = await store.get_active_by_email(principal.subject)
        if actor is None:
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                "Пользователь не найден или деактивирован",
            )
        if require_admin:
            is_admin = principal.is_admin if principal.is_admin is not None else actor.is_admin
            if not is_admin:
                raise ForbiddenError()
        return actor


async def _abort_app_error(context: grpc.aio.ServicerContext, exc: AppError) -> None:
    await context.abort(
        _APP_TO_GRPC_STATUS.get(exc.status_code, grpc.StatusCode.INTERNAL),
        f"{exc.code}: {exc.message}",
    )


class SystemGrpcService(pb2_grpc.SystemServiceServicer):
    async def Health(self, _: Empty, __) -> pb2.HealthResponse:
        return pb2.HealthResponse(status="ok")


class ProjectGrpcService(pb2_grpc.ProjectServiceServicer):
    async def ListProjects(
        self,
        _: Empty,
        context: grpc.aio.ServicerContext,
    ) -> pb2.ProjectListResponse:
        try:
            await _require_actor(context=context)
            async with _session_scope() as session:
                service = ProjectService(ProjectRepository(session))
                response = await service.list_projects()
            return pb2.ProjectListResponse(
                items=[to_proto_project(item) for item in response.items],
                total=response.total,
            )
        except AppError as exc:
            await _abort_app_error(context, exc)
            raise


class TaskGrpcService(pb2_grpc.TaskServiceServicer):
    async def ListTasks(
        self, request: pb2.ListTasksRequest, context: grpc.aio.ServicerContext
    ) -> pb2.ListTasksResponse:
        try:
            await _require_actor(context=context)
            params = TaskListParams(
                project_id=uuid.UUID(request.project_id) if request.project_id else None,
                parent_task_id=(
                    uuid.UUID(request.parent_task_id) if request.parent_task_id else None
                ),
                root_only=request.root_only,
                leaves_only=request.leaves_only,
                status=request.status or None,
                assignee=request.assignee or None,
                priority=request.priority or None,
                q=request.q or None,
                tag=request.tag or None,
                sort_by=request.sort_by or "created_at",
                sort_order=request.sort_order or "desc",
                page=request.page or 1,
                page_size=request.page_size or 20,
            )
            async with _session_scope() as session:
                refs = get_task_ref_registry()
                service = TaskService(
                    repository=TaskRepository(session, refs),
                    projects=ProjectRepository(session),
                    users=build_user_store(session),
                    history=TaskHistoryRecorder(TaskHistoryRepository(session)),
                    comments=TaskCommentRepository(session),
                    cache=TaskListCache(get_redis()),
                    refs=refs,
                )
                response = await service.list_tasks(params)
            return pb2.ListTasksResponse(
                items=[to_proto_task(item) for item in response.items],
                total=response.total,
                page=response.page,
                page_size=response.page_size,
                pages=response.pages,
            )
        except AppError as exc:
            await _abort_app_error(context, exc)
            raise

    async def CreateTask(
        self, request: pb2.CreateTaskRequest, context: grpc.aio.ServicerContext
    ) -> pb2.Task:
        try:
            actor = await _require_actor(context=context)
            start_at = request.start_at.ToDatetime() if request.HasField("start_at") else None
            end_at = request.end_at.ToDatetime() if request.HasField("end_at") else None
            data = TaskCreate(
                project_id=uuid.UUID(request.project_id),
                title=request.title,
                assignee=request.assignee,
                parent_task_id=(
                    uuid.UUID(request.parent_task_id) if request.parent_task_id else None
                ),
                description=request.description or None,
                priority=request.priority or "medium",
                start_at=start_at,
                end_at=end_at,
                tags=list(request.tags),
            )
            async with _session_scope() as session:
                refs = get_task_ref_registry()
                service = TaskService(
                    repository=TaskRepository(session, refs),
                    projects=ProjectRepository(session),
                    users=build_user_store(session),
                    history=TaskHistoryRecorder(TaskHistoryRepository(session)),
                    comments=TaskCommentRepository(session),
                    cache=TaskListCache(get_redis()),
                    refs=refs,
                )
                created = await service.create(data, actor=actor)
            return to_proto_task(created)
        except AppError as exc:
            await _abort_app_error(context, exc)
            raise
