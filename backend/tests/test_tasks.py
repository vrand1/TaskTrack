import pytest
from httpx import AsyncClient

from tests.users import AdminUser, NormalUser


def _task_payload(project_id: str, **extra: object) -> dict:
    return {
        "project_id": project_id,
        "title": "Task",
        "assignee": NormalUser.email,
        **extra,
    }


@pytest.mark.asyncio
async def test_create_task(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Implement API",
            "description": "CRUD for tasks",
            "assignee": AdminUser.email,
            "priority": "high",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Implement API"
    assert body["assignee"] == AdminUser.email
    assert body["status"] == "todo"
    assert body["was_reopened"] is False
    assert body["priority"] == "high"
    assert body["project_id"] == project_id
    assert body["parent_task_id"] is None
    assert "id" in body


@pytest.mark.asyncio
async def test_create_task_unknown_assignee(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, assignee="unknown@example.dev"),
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_ASSIGNEE"


@pytest.mark.asyncio
async def test_status_transition(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    create = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Task"),
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    for status in ("in_progress", "review", "done"):
        response = await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": status},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.asyncio
async def test_cannot_transition_from_done(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    create = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Done task"),
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    for status in ("in_progress", "review", "done"):
        await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": status},
            headers=auth_headers,
        )

    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "review"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_cannot_reopen_via_status_patch(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    create = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Done task"),
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    for status in ("in_progress", "review", "done"):
        await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": status},
            headers=auth_headers,
        )

    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "todo"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_reopen_from_done_sets_flag(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    create = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Reopenable task"),
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    for status in ("in_progress", "review", "done"):
        response = await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": status},
            headers=auth_headers,
        )
        assert response.status_code == 200

    response = await client.post(
        f"/api/v1/tasks/{task_id}/reopen",
        headers=auth_headers,
    )
    assert response.status_code == 200

    reopened = response.json()
    assert reopened["status"] == "todo"
    assert reopened["was_reopened"] is True


@pytest.mark.asyncio
async def test_cannot_reopen_twice(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    create = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Second reopen blocked"),
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    for status in ("in_progress", "review", "done"):
        await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": status},
            headers=auth_headers,
        )

    first = await client.post(f"/api/v1/tasks/{task_id}/reopen", headers=auth_headers)
    assert first.status_code == 200

    for status in ("in_progress", "review", "done"):
        await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": status},
            headers=auth_headers,
        )

    second = await client.post(f"/api/v1/tasks/{task_id}/reopen", headers=auth_headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "TASK_ALREADY_REOPENED"


@pytest.mark.asyncio
async def test_reopen_requires_done_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    create = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="Active task"),
        headers=auth_headers,
    )
    task_id = create.json()["id"]

    response = await client.post(
        f"/api/v1/tasks/{task_id}/reopen",
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_NOT_REOPENABLE"


@pytest.mark.asyncio
async def test_list_filter_and_soft_delete(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="A", assignee=AdminUser.email),
        headers=auth_headers,
    )
    second = await client.post(
        "/api/v1/tasks",
        json=_task_payload(project_id, title="B"),
        headers=auth_headers,
    )
    task_id = second.json()["id"]

    listed = await client.get(
        "/api/v1/tasks",
        params={"assignee": AdminUser.email},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    deleted = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert deleted.status_code == 204

    get_deleted = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert get_deleted.status_code == 404
