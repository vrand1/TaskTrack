import pytest
from httpx import AsyncClient

from tests.users import AdminUser


@pytest.mark.asyncio
async def test_create_and_get_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/projects",
        json={"name": "Backend", "slug": "backend", "description": "API work"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == "backend"
    assert body["name"] == "Backend"
    assert body["created_by"] == AdminUser.email

    fetched = await client.get(f"/api/v1/projects/{body['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["slug"] == "backend"

    deleted = await client.delete(f"/api/v1/projects/{body['id']}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_list_projects(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/api/v1/projects",
        json={"name": "Listed", "slug": "listed"},
        headers=auth_headers,
    )
    project_id = created.json()["id"]

    response = await client.get("/api/v1/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == project_id

    await client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
