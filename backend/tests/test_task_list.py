import pytest
from httpx import AsyncClient

from tests.users import AdminUser, NormalUser


@pytest.mark.asyncio
async def test_list_all_tasks_pagination(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    for index in range(3):
        await client.post(
            "/api/v1/tasks",
            json={
                "project_id": project_id,
                "title": f"Task {index}",
                "assignee": AdminUser.email,
            },
            headers=auth_headers,
        )

    page1 = await client.get(
        "/api/v1/tasks",
        params={"page": 1, "page_size": 2},
        headers=auth_headers,
    )
    assert page1.status_code == 200
    body = page1.json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2

    page2 = await client.get(
        "/api/v1/tasks",
        params={"page": 2, "page_size": 2},
        headers=auth_headers,
    )
    assert len(page2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_user_tasks_and_leaves(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    parent = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Parent epic",
            "assignee": NormalUser.email,
        },
        headers=auth_headers,
    )
    parent_id = parent.json()["id"]

    await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Leaf task",
            "assignee": NormalUser.email,
            "parent_task_id": parent_id,
        },
        headers=auth_headers,
    )

    normal_user_path = NormalUser.email.replace("@", "%40")
    all_bob = await client.get(f"/api/v1/users/{normal_user_path}/tasks", headers=auth_headers)
    assert all_bob.status_code == 200
    assert all_bob.json()["total"] == 2

    leaves = await client.get(
        f"/api/v1/users/{normal_user_path}/tasks/leaves",
        headers=auth_headers,
    )
    assert leaves.status_code == 200
    assert leaves.json()["total"] == 1
    assert leaves.json()["items"][0]["title"] == "Leaf task"

    me_leaves = await client.get("/api/v1/tasks/me/leaves", headers=auth_headers)
    assert me_leaves.status_code == 200
    assert me_leaves.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_unknown_user_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/api/v1/users/nobody/tasks", headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_ASSIGNEE"
