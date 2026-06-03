import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from app.core.idempotency import IdempotencyServiceDep, request_body_hash
from app.domains.auth.dependencies import CurrentUserDep
from app.domains.projects.dependencies import ProjectServiceDep
from app.domains.projects.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectRead,
    ProjectUpdate,
)
from app.shared.schemas.pagination import PaginationParams

router = APIRouter(prefix="/projects", tags=["projects"])


IdempotencyKeyHeader = Annotated[
    str | None,
    Header(alias="Idempotency-Key", max_length=128),
]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    service: ProjectServiceDep,
    actor: CurrentUserDep,
    idempotency: IdempotencyServiceDep,
    idempotency_key: IdempotencyKeyHeader = None,
) -> ProjectRead:
    async def handler() -> ProjectRead:
        project = await service.create(data, actor=actor)
        return ProjectRead.from_db(project)

    result = await idempotency.run(
        key=idempotency_key,
        scope="POST /projects",
        request_hash=request_body_hash(data),
        handler=handler,
        status_code=status.HTTP_201_CREATED,
        response_type=ProjectRead,
    )
    return result  # type: ignore[return-value]


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    service: ProjectServiceDep,
    _: CurrentUserDep,
    pagination: Annotated[PaginationParams, Depends()],
) -> ProjectListResponse:
    return await service.list_projects(pagination)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
    _: CurrentUserDep,
) -> ProjectRead:
    project = await service.get_by_id(project_id)
    return ProjectRead.from_db(project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    service: ProjectServiceDep,
    _: CurrentUserDep,
) -> ProjectRead:
    project = await service.update(project_id, data)
    return ProjectRead.from_db(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
    _: CurrentUserDep,
) -> Response:
    await service.delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/restore", response_model=ProjectRead)
async def restore_project(
    project_id: uuid.UUID,
    service: ProjectServiceDep,
    _: CurrentUserDep,
) -> ProjectRead:
    project = await service.restore(project_id)
    return ProjectRead.from_db(project)
