import pytest
from httpx import AsyncClient

from tests.users import TEST_PASSWORD, NormalUser


@pytest.mark.asyncio
async def test_admin_can_create_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "carol@example.dev",
            "password": TEST_PASSWORD,
            "is_active": True,
            "is_admin": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "carol@example.dev"
    assert body["is_active"] is True
    assert body["is_admin"] is False
    assert "password" not in body

    login = await client.post(
        "/api/v1/auth/token",
        json={"email": "carol@example.dev", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_admin_sync_user_by_email(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    response = await client.post(
        "/api/v1/users/sync",
        json={"email": "synced@example.dev", "is_active": True, "is_admin": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["email"] == "synced@example.dev"

    task = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "For synced user",
            "assignee": "synced@example.dev",
        },
        headers=auth_headers,
    )
    assert task.status_code == 201


@pytest.mark.asyncio
async def test_non_admin_cannot_create_user(
    client: AsyncClient,
    normal_user_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"email": "dave@example.dev", "password": TEST_PASSWORD},
        headers=normal_user_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_user_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"email": "eve@example.dev", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"email": NormalUser.email, "password": TEST_PASSWORD},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"
