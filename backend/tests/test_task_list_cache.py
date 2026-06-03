import pytest
from fakeredis.aioredis import FakeRedis

from app.cache.task_list import TaskListCache, build_list_cache_key
from app.domains.tasks.params.list import TaskListParams
from app.domains.tasks.schemas import TaskListResponse
from tests.users import AdminUser, NormalUser


@pytest.mark.asyncio
async def test_cache_roundtrip() -> None:
    redis = FakeRedis(decode_responses=True)
    cache = TaskListCache(redis)
    params = TaskListParams(status="todo", assignee=AdminUser.email, page=1, page_size=20)
    payload = TaskListResponse.build(items=[], total=0, page=1, page_size=20)

    await cache.set(params, payload)
    loaded = await cache.get(params)

    assert loaded == payload
    assert build_list_cache_key(params) == (
        f"tasks:list:project=:parent=:root=0:leaves=0:status=todo:assignee={AdminUser.email}:"
        "priority=:q=:tag=:sort=created_at:desc:page=1:size=20"
    )


@pytest.mark.asyncio
async def test_cache_invalidate_all() -> None:
    redis = FakeRedis(decode_responses=True)
    cache = TaskListCache(redis)
    params_a = TaskListParams(page=1, page_size=20)
    params_b = TaskListParams(status="done", assignee=NormalUser.email, page=2, page_size=10)
    payload = TaskListResponse.build(items=[], total=0, page=1, page_size=20)

    await cache.set(params_a, payload)
    await cache.set(params_b, payload)
    await cache.invalidate_all()

    assert await cache.get(params_a) is None
    assert await cache.get(params_b) is None
