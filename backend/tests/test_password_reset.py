import pytest
from httpx import AsyncClient

from tests.users import TEST_PASSWORD, AdminUser, NormalUser

NEW_PASSWORD = "newpassword123"


@pytest.mark.asyncio
async def test_user_changes_own_password(
    client: AsyncClient,
    normal_user_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        headers=normal_user_headers,
    )
    assert response.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/token",
        json={"email": NormalUser.email, "password": TEST_PASSWORD},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/token",
        json={"email": NormalUser.email, "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_user_wrong_current_password(
    client: AsyncClient,
    normal_user_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
        headers=normal_user_headers,
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CURRENT_PASSWORD"


@pytest.mark.asyncio
async def test_admin_resets_user_password(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/users/{NormalUser.email}/password",
        json={"new_password": NEW_PASSWORD},
        headers=auth_headers,
    )
    assert response.status_code == 204

    login = await client.post(
        "/api/v1/auth/token",
        json={"email": NormalUser.email, "password": NEW_PASSWORD},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_admin_reset_unknown_user(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/users/nobody@example.dev/password",
        json={"new_password": NEW_PASSWORD},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_non_admin_cannot_reset_other_password(
    client: AsyncClient,
    normal_user_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/users/{AdminUser.email}/password",
        json={"new_password": NEW_PASSWORD},
        headers=normal_user_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_password_reset_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_disabled_for_external_auth(
    client: AsyncClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "auth_provider", "external")

    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        headers=auth_headers,
    )
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "EXTERNAL_AUTH_PROVIDER"
