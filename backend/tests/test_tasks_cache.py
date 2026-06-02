import json

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient

from tests.users import AdminUser


@pytest.mark.asyncio
async def test_list_tasks_uses_cache(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
    fake_redis: FakeRedis,
) -> None:
    await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Cached",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )

    keys_before = [key async for key in fake_redis.scan_iter(match="tasks:list:*")]
    assert keys_before == []

    first = await client.get("/api/v1/tasks", headers=auth_headers)
    assert first.status_code == 200
    assert first.json()["total"] == 1

    keys_after_warm = [key async for key in fake_redis.scan_iter(match="tasks:list:*")]
    assert len(keys_after_warm) == 1
    cached_payload = json.loads(await fake_redis.get(keys_after_warm[0]))
    assert cached_payload["total"] == 1

    second = await client.get("/api/v1/tasks", headers=auth_headers)
    assert second.status_code == 200
    assert second.json() == first.json()

    keys_after_second = [key async for key in fake_redis.scan_iter(match="tasks:list:*")]
    assert keys_after_second == keys_after_warm


@pytest.mark.asyncio
async def test_tasks_write_invalidates_list_cache(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
    fake_redis: FakeRedis,
) -> None:
    await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Task 1",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )

    warm = await client.get("/api/v1/tasks", headers=auth_headers)
    assert warm.status_code == 200
    assert warm.json()["total"] == 1

    keys_before = [key async for key in fake_redis.scan_iter(match="tasks:list:*")]
    assert keys_before

    created = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Task 2",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201

    keys_after_write = [key async for key in fake_redis.scan_iter(match="tasks:list:*")]
    assert keys_after_write == []

    refreshed = await client.get("/api/v1/tasks", headers=auth_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["total"] == 2
