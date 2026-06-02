import asyncio
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.domains.projects.model import Project
from app.domains.tasks.models import Task


def _cutoff_for_dialect(cutoff: datetime, dialect_name: str) -> datetime:
    if dialect_name == "sqlite":
        return cutoff.replace(tzinfo=None)
    return cutoff


class SoftDeletePurgeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(self) -> tuple[int, int]:
        cutoff = datetime.now(UTC) - timedelta(days=settings.soft_delete_retention_days)
        dialect = self._session.get_bind().dialect.name
        cutoff_db = _cutoff_for_dialect(cutoff, dialect)
        tasks_removed = await self._purge_tasks(cutoff_db)
        projects_removed = await self._purge_projects(cutoff_db)
        return tasks_removed, projects_removed

    async def _purge_tasks(self, cutoff: datetime) -> int:
        expired_ids = select(Task.id).where(
            Task.deleted_at.is_not(None),
            Task.deleted_at < cutoff,
        )
        await self._session.execute(
            update(Task).where(Task.parent_task_id.in_(expired_ids)).values(parent_task_id=None)
        )
        result = await self._session.execute(
            delete(Task)
            .where(
                Task.deleted_at.is_not(None),
                Task.deleted_at < cutoff,
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount or 0

    async def _purge_projects(self, cutoff: datetime) -> int:
        projects_with_tasks = select(Task.project_id).distinct()
        result = await self._session.execute(
            delete(Project)
            .where(
                Project.deleted_at.is_not(None),
                Project.deleted_at < cutoff,
                Project.id.not_in(projects_with_tasks),
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount or 0


async def purge_expired_soft_deleted() -> None:
    async with async_session_factory() as session:
        try:
            tasks_removed, projects_removed = await SoftDeletePurgeService(session).run()
            await session.commit()
            if tasks_removed or projects_removed:
                logger.info(
                    "Purged soft-deleted rows older than {} days: tasks={}, projects={}",
                    settings.soft_delete_retention_days,
                    tasks_removed,
                    projects_removed,
                )
        except Exception:
            await session.rollback()
            logger.exception("Soft-delete purge failed")


async def run_purge_worker(stop_event: asyncio.Event) -> None:
    interval_seconds = settings.soft_delete_purge_interval_hours * 3600
    while not stop_event.is_set():
        await purge_expired_soft_deleted()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue
