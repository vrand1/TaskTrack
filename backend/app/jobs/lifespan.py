import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cache.redis_client import close_redis, init_redis
from app.core.config import settings
from app.db.session import async_session_factory, engine
from app.domains.tasks.refs import init_task_ref_registry
from app.grpc import GrpcServer
from app.jobs.purge_soft_deleted import purge_expired_soft_deleted, run_purge_worker


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    if getattr(app.state, "test_session_factory", None) is not None:
        yield
        return

    await init_redis()
    async with async_session_factory() as session:
        await init_task_ref_registry(session)
    await purge_expired_soft_deleted()

    stop_event = asyncio.Event()
    purge_task = asyncio.create_task(run_purge_worker(stop_event))
    grpc_server = GrpcServer() if settings.grpc_enabled else None
    if grpc_server is not None:
        await grpc_server.start()
    try:
        yield
    finally:
        stop_event.set()
        purge_task.cancel()
        try:
            await purge_task
        except asyncio.CancelledError:
            pass
        if grpc_server is not None:
            await grpc_server.stop()
        await close_redis()
        await engine.dispose()
