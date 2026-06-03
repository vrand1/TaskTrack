import uuid

from app.core.exceptions import ProjectSlugTakenError
from app.domains.projects.model import Project
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectPaginationParams,
    ProjectRead,
    ProjectUpdate,
)
from app.domains.projects.utils import slugify
from app.domains.users.model import User


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    async def create(self, data: ProjectCreate, *, actor: User) -> Project:
        slug = slugify(data.slug or data.name)
        if await self._repository.slug_exists(slug):
            raise ProjectSlugTakenError(slug)

        project = Project(
            slug=slug,
            name=data.name,
            description=data.description,
            created_by_id=actor.id,
        )
        return await self._repository.add(project)

    async def get_by_id(self, project_id: uuid.UUID) -> Project:
        return await self._repository.get_active_by_id(project_id)

    async def list_projects(self, pagination: ProjectPaginationParams) -> ProjectListResponse:
        projects, total = await self._repository.list_active(
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return ProjectListResponse.build(
            items=[ProjectRead.from_db(project) for project in projects],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def update(self, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        project = await self._repository.get_active_by_id(project_id)
        updates = data.model_dump(exclude_unset=True)

        if "slug" in updates:
            slug_raw = updates.pop("slug")
            if slug_raw is not None: 
                slug = slugify(slug_raw)
                if await self._repository.slug_exists(slug, exclude_id=project.id):
                    raise ProjectSlugTakenError(slug) # Есть ограничение на уровне модели, да.
                                                      # Здесь для понятной ошибки
                project.slug = slug

        for field, value in updates.items():
            setattr(project, field, value)

        return await self._repository.save(project)

    async def delete(self, project_id: uuid.UUID) -> None:
        project = await self._repository.get_active_by_id(project_id)
        await self._repository.soft_delete(project)

    async def restore(self, project_id: uuid.UUID) -> Project:
        project = await self._repository.get_restorable(project_id)
        return await self._repository.restore(project)
