import pytest
from httpx import AsyncClient

from tests.users import AdminUser, NormalUser


@pytest.mark.asyncio
async def test_subtasks_and_tree(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    parent = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Parent",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )
    parent_id = parent.json()["id"]

    child = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Child",
            "assignee": NormalUser.email,
            "parent_task_id": parent_id,
        },
        headers=auth_headers,
    )
    child_id = child.json()["id"]
    assert child.json()["parent_task_id"] == parent_id

    subtasks = await client.get(f"/api/v1/tasks/{parent_id}/subtasks", headers=auth_headers)
    assert subtasks.status_code == 200
    assert subtasks.json()["total"] == 1
    assert subtasks.json()["items"][0]["id"] == child_id

    tree = await client.get(
        f"/api/v1/tasks/{parent_id}",
        params={"include_subtasks": True},
        headers=auth_headers,
    )
    assert tree.status_code == 200
    assert len(tree.json()["subtasks"]) == 1
    assert tree.json()["subtasks"][0]["title"] == "Child"


@pytest.mark.asyncio
async def test_parent_must_be_same_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    other_project = await client.post(
        "/api/v1/projects",
        json={"name": "Other"},
        headers=auth_headers,
    )
    other_project_id = other_project.json()["id"]

    parent = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": other_project_id,
            "title": "Elsewhere",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )

    response = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Bad child",
            "assignee": NormalUser.email,
            "parent_task_id": parent.json()["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARENT_TASK"


@pytest.mark.asyncio
async def test_task_history_on_status_change(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    created = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Tracked",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )
    task_id = created.json()["id"]

    await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers=auth_headers,
    )

    history = await client.get(f"/api/v1/tasks/{task_id}/history", headers=auth_headers)
    assert history.status_code == 200
    body = history.json()
    events = body["items"]
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert events[0]["event_type"] == "created"
    assert events[0]["actor"] == AdminUser.email
    assert events[1]["event_type"] == "status_changed"
    assert events[1]["payload"] == {"from": "todo", "to": "in_progress", "reopened": False}


@pytest.mark.asyncio
async def test_task_history_filters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    created = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Filter history",
            "assignee": AdminUser.email,
        },
        headers=auth_headers,
    )
    task_id = created.json()["id"]

    await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Renamed"},
        headers=auth_headers,
    )

    by_type = await client.get(
        f"/api/v1/tasks/{task_id}/history",
        params={"event_type": "status_changed"},
        headers=auth_headers,
    )
    assert by_type.status_code == 200
    assert by_type.json()["total"] == 1
    assert by_type.json()["items"][0]["event_type"] == "status_changed"

    by_actor = await client.get(
        f"/api/v1/tasks/{task_id}/history",
        params={"actor": AdminUser.email, "event_type": "created"},
        headers=auth_headers,
    )
    assert by_actor.status_code == 200
    assert by_actor.json()["total"] == 1
    assert by_actor.json()["items"][0]["event_type"] == "created"

    newest_first = await client.get(
        f"/api/v1/tasks/{task_id}/history",
        params={"sort": "desc", "page": 1, "page_size": 2},
        headers=auth_headers,
    )
    assert newest_first.status_code == 200
    assert newest_first.json()["total"] == 3
    assert newest_first.json()["pages"] == 2
    assert newest_first.json()["items"][0]["event_type"] == "updated"

    invalid_type = await client.get(
        f"/api/v1/tasks/{task_id}/history",
        params={"event_type": "unknown"},
        headers=auth_headers,
    )
    assert invalid_type.status_code == 422
