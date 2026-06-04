from redis.asyncio import Redis

from app.core.config import settings

# Да, Singleton, вроде бы антипаттерн, но это буквально инстанс для кеша
# От него не зависит истинность данных/процессов, и он не зависит от других сервисов
# И проблемы с ним могут возникнуть только из-за ошибок окружения (сервер, контейнер etc)
# а не из-за ошибок доменной логики 

_redis: Redis | None = None 


async def init_redis() -> None:
    global _redis
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis не инициализирован")
    return _redis
