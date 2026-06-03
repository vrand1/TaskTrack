import pytest
from httpx import AsyncClient

from tests.users import NormalUser


def _task_payload(project_id: str, **extra: object) -> dict:
    return {
        "project_id": project_id,
        "title": "Task",
        "assignee": NormalUser.email,
        **extra,
    }


@pytest.mark.asyncio
async def test_list_tags_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/api/v1/tags", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_tags_after_task_create(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Tagged", tags=["backend", "urgent"]),
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Also tagged", tags=["backend", "qa"]),
        headers=auth_headers,
    )

    response = await client.get("/api/v1/tags", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["name"] for item in body["items"]] == ["backend", "qa", "urgent"]
    assert all("id" in item for item in body["items"])


@pytest.mark.asyncio
async def test_list_tags_search(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, tags=["backend", "frontend"]),
        headers=auth_headers,
    )

    response = await client.get("/api/v1/tags", params={"q": "back"}, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "backend"


@pytest.mark.asyncio
async def test_list_tags_by_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    other_project = await client.post(
        "/api/v1/projects",
        json={"name": "Other", "slug": "other-tags"},
        headers=auth_headers,
    )
    other_project_id = other_project.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, tags=["in-main"]),
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/tasks",
        json=_task_payload(other_project_id, tags=["in-other"]),
        headers=auth_headers,
    )

    response = await client.get(
        "/api/v1/tags",
        params={"project_id": project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "in-main"


@pytest.mark.asyncio
async def test_list_tags_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tags")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_tags_unknown_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/tags",
        params={"project_id": "00000000-0000-4000-8000-000000000099"},
        headers=auth_headers,
    )
    assert response.status_code == 404
