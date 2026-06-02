from redis.asyncio import Redis

from app.core.config import settings
from app.domains.tasks.list_params import TaskListParams
from app.domains.tasks.schemas import TaskListResponse

LIST_KEY_PREFIX = "tasks:list:"


def build_list_cache_key(params: TaskListParams) -> str:
    return (
        f"{LIST_KEY_PREFIX}"
        f"project={params.project_id or ''}:"
        f"parent={params.parent_task_id or ''}:"
        f"root={int(params.root_only)}:"
        f"leaves={int(params.leaves_only)}:"
        f"status={params.status or ''}:"
        f"assignee={params.assignee or ''}:"
        f"priority={params.priority or ''}:"
        f"q={params.q or ''}:"
        f"tag={params.tag or ''}:"
        f"sort={params.sort_by}:{params.sort_order}:"
        f"page={params.page}:"
        f"size={params.page_size}"
    )


class TaskListCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, params: TaskListParams) -> TaskListResponse | None:
        cached = await self._redis.get(build_list_cache_key(params))
        if cached is None:
            return None
        return TaskListResponse.model_validate_json(cached)

    async def set(self, params: TaskListParams, payload: TaskListResponse) -> None:
        await self._redis.set(
            build_list_cache_key(params),
            payload.model_dump_json(),
            ex=settings.redis_tasks_list_ttl_seconds,
        )

    async def invalidate_all(self) -> None:
        async for key in self._redis.scan_iter(match=f"{LIST_KEY_PREFIX}*"):
            await self._redis.delete(key)
