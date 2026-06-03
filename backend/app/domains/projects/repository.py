import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.datetime_utils import ensure_utc
from app.core.exceptions import ProjectNotFoundError, ProjectSlugTakenError, RestoreExpiredError
from app.domains.projects.model import Project
from app.shared.query.pagination import OffsetPagination

PROJECT_LOAD = (selectinload(Project.created_by),)


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> Project:
        self._session.add(project)
        await self._session.flush()
        return await self.get_active_by_id(project.id)

    async def get_active_by_id(self, project_id: uuid.UUID) -> Project:
        result = await self._session.execute(
            select(Project)
            .options(*PROJECT_LOAD)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return project

    async def get_active_by_slug(self, slug: str) -> Project | None:
        result = await self._session.execute(
            select(Project)
            .options(*PROJECT_LOAD)
            .where(Project.slug == slug, Project.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        query = (
            select(func.count())
            .select_from(Project)
            .where(
                Project.slug == slug,
                Project.deleted_at.is_(None),
            )
        )
        if exclude_id is not None:
            query = query.where(Project.id != exclude_id)
        count = await self._session.scalar(query)
        return bool(count)

    async def list_active(self, params: OffsetPagination) -> tuple[list[Project], int]:
        query = (
            select(Project)
            .options(*PROJECT_LOAD)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        count_query = select(func.count()).select_from(Project).where(Project.deleted_at.is_(None))
        total = await self._session.scalar(count_query) or 0
        result = await self._session.scalars(query)
        return list(result.all()), total

    async def save(self, project: Project) -> Project:
        project.updated_at = datetime.now(UTC)
        await self._session.flush()
        return await self.get_active_by_id(project.id)

    async def soft_delete(self, project: Project) -> None:
        project.deleted_at = datetime.now(UTC)
        project.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def get_restorable(self, project_id: uuid.UUID) -> Project:
        result = await self._session.execute(
            select(Project)
            .options(*PROJECT_LOAD)
            .where(Project.id == project_id, Project.deleted_at.is_not(None))
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        cutoff = datetime.now(UTC) - timedelta(days=settings.soft_delete_retention_days)
        if ensure_utc(project.deleted_at) < cutoff:
            raise RestoreExpiredError(
                entity="Project",
                retention_days=settings.soft_delete_retention_days,
            )
        return project

    async def restore(self, project: Project) -> Project:
        if await self.slug_exists(project.slug, exclude_id=project.id):
            raise ProjectSlugTakenError(project.slug)
        project.deleted_at = None
        project.updated_at = datetime.now(UTC)
        await self._session.flush()
        return await self.get_active_by_id(project.id)
