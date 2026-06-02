import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_session
from app.domains.tasks.models import Task
from app.jobs.purge_soft_deleted import SoftDeletePurgeService
from app.main import app
from tests.users import AdminUser

pytestmark = pytest.mark.asyncio


def _past_retention_deadline() -> datetime:
    deadline = datetime.now(UTC) - timedelta(days=settings.soft_delete_retention_days + 1)
    return deadline.replace(tzinfo=None)


async def _session_factory():
    override = app.dependency_overrides.get(get_session)
    assert override is not None
    gen = override()
    session = await gen.__anext__()
    return session, gen


async def test_restore_task_within_retention(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    created = await client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Restore me", "assignee": AdminUser.email},
        headers=auth_headers,
    )
    task_id = created.json()["id"]
    await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)

    restored = await client.post(f"/api/v1/tasks/{task_id}/restore", headers=auth_headers)
    assert restored.status_code == 200
    assert restored.json()["title"] == "Restore me"

    history = await client.get(f"/api/v1/tasks/{task_id}/history", headers=auth_headers)
    types = [item["event_type"] for item in history.json()["items"]]
    assert "restored" in types


async def test_restore_expired_returns_410(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    created = await client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Too old", "assignee": AdminUser.email},
        headers=auth_headers,
    )
    task_id = uuid.UUID(created.json()["id"])

    session, gen = await _session_factory()
    try:
        task = await session.get(Task, task_id)
        assert task is not None
        task.deleted_at = _past_retention_deadline()
        await session.commit()
    finally:
        await gen.aclose()

    response = await client.post(f"/api/v1/tasks/{task_id}/restore", headers=auth_headers)
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "RESTORE_EXPIRED"


async def test_purge_removes_expired_soft_deleted(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    created = await client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Purge me", "assignee": AdminUser.email},
        headers=auth_headers,
    )
    task_id = uuid.UUID(created.json()["id"])
    await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)

    session, gen = await _session_factory()
    try:
        task = await session.get(Task, task_id)
        assert task is not None
        task.deleted_at = _past_retention_deadline()
        await session.commit()

        removed, _ = await SoftDeletePurgeService(session).run()
        await session.commit()
        assert removed == 1

        remaining = await session.scalar(select(Task).where(Task.id == task_id))
        assert remaining is None
    finally:
        await gen.aclose()

    get_resp = await client.post(f"/api/v1/tasks/{task_id}/restore", headers=auth_headers)
    assert get_resp.status_code == 404
