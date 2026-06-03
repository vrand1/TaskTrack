import uuid
from collections.abc import AsyncIterator

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cache import redis_client
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.domains.tasks.domain.constants import TASK_PRIORITIES, TASK_STATUSES
from app.domains.tasks.domain.refs import init_task_ref_registry, reset_task_ref_registry_for_tests
from app.domains.tasks.models import Task, TaskEvent, TaskPriorityRef, TaskStatusRef  # noqa: F401
from app.domains.users.model import User
from app.main import app
from tests.users import TEST_PASSWORD, AdminUser, NormalUser, TestUser

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

STATUS_SORT_ORDER = {code: index + 1 for index, code in enumerate(TASK_STATUSES)}


async def _seed(session) -> None:
    password_hash = hash_password(TEST_PASSWORD)
    session.add_all(
        [
            User(
                id=AdminUser.id,
                email=AdminUser.email,
                password_hash=password_hash,
                is_active=True,
                is_admin=AdminUser.is_admin,
            ),
            User(
                id=NormalUser.id,
                email=NormalUser.email,
                password_hash=password_hash,
                is_active=True,
                is_admin=NormalUser.is_admin,
            ),
        ]
    )
    for code in TASK_STATUSES:
        session.add(
            TaskStatusRef(
                id=STATUS_SORT_ORDER[code],
                code=code,
                sort_order=STATUS_SORT_ORDER[code],
            )
        )
    for index, code in enumerate(TASK_PRIORITIES, start=1):
        session.add(TaskPriorityRef(id=index, code=code))


async def _login_headers(client: AsyncClient, user: TestUser) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/token",
        json={"email": user.email, "password": user.password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> AsyncIterator[str]:
    slug = f"test-{uuid.uuid4().hex[:12]}"
    created = await client.post(
        "/api/v1/projects",
        json={"name": "Test project", "slug": slug},
        headers=auth_headers,
    )
    assert created.status_code == 201
    pid = created.json()["id"]
    yield pid
    await client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)


@pytest.fixture
async def fake_redis():
    redis = FakeRedis(decode_responses=True)
    redis_client._redis = redis
    yield redis
    await redis.aclose()
    redis_client._redis = None


@pytest.fixture
async def client(fake_redis) -> AsyncClient:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.test_session_factory = session_factory

    async with session_factory() as session:
        await _seed(session)
        await session.commit()
        await init_task_ref_registry(session)

    async def override_get_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    app.state.test_session_factory = None
    reset_task_ref_registry_for_tests()
    await engine.dispose()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    return await _login_headers(client, AdminUser)


@pytest.fixture
async def normal_user_headers(client: AsyncClient) -> dict[str, str]:
    return await _login_headers(client, NormalUser)
