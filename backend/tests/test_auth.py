import pytest
from httpx import AsyncClient

from tests.users import TEST_PASSWORD, AdminUser


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/token",
        json={"email": AdminUser.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/token",
        json={"email": AdminUser.email, "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_tasks_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
