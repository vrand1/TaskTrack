import uuid

import pytest
from httpx import AsyncClient

from tests.users import AdminUser


@pytest.mark.asyncio
async def test_list_search_sort_and_tag_filter(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    alpha = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Alpha release",
            "assignee": AdminUser.email,
            "tags": ["backend", "urgent"],
        },
        headers=auth_headers,
    )
    assert alpha.status_code == 201

    await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Beta test",
            "assignee": AdminUser.email,
            "tags": ["qa"],
        },
        headers=auth_headers,
    )

    search = await client.get(
        "/api/v1/tasks",
        params={"q": "alpha"},
        headers=auth_headers,
    )
    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["items"][0]["title"] == "Alpha release"

    by_tag = await client.get(
        "/api/v1/tasks",
        params={"tag": "urgent"},
        headers=auth_headers,
    )
    assert by_tag.status_code == 200
    assert by_tag.json()["total"] == 1
    assert "urgent" in by_tag.json()["items"][0]["tags"]

    sorted_resp = await client.get(
        "/api/v1/tasks",
        params={"sort_by": "title", "sort_order": "asc"},
        headers=auth_headers,
    )
    titles = [item["title"] for item in sorted_resp.json()["items"]]
    assert titles == sorted(titles)


@pytest.mark.asyncio
async def test_task_date_range_and_comments(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    start_at = "2026-12-30T12:00:00+00:00"
    end_at = "2026-12-31T12:00:00+00:00"
    created = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "With deadline",
            "assignee": AdminUser.email,
            "start_at": start_at,
            "end_at": end_at,
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["start_at"] is not None
    assert created.json()["end_at"] is not None

    comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"body": "Need review"},
        headers=auth_headers,
    )
    assert comment.status_code == 201
    assert comment.json()["body"] == "Need review"

    comments = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=auth_headers)
    assert comments.status_code == 200
    assert comments.json()["total"] == 1

    history = await client.get(
        f"/api/v1/tasks/{task_id}/history",
        params={"event_type": "comment_added"},
        headers=auth_headers,
    )
    assert history.status_code == 200
    assert history.json()["total"] == 1


@pytest.mark.asyncio
async def test_task_date_range_validation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Invalid dates",
            "assignee": AdminUser.email,
            "start_at": "2026-12-31T12:00:00+00:00",
            "end_at": "2026-12-30T12:00:00+00:00",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_idempotency_create_task(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    key = str(uuid.uuid4())
    payload = {
        "project_id": project_id,
        "title": "Idempotent task",
        "assignee": AdminUser.email,
    }
    headers = {**auth_headers, "Idempotency-Key": key}

    first = await client.post("/api/v1/tasks", json=payload, headers=headers)
    second = await client.post("/api/v1/tasks", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    conflict = await client.post(
        "/api/v1/tasks",
        json={**payload, "title": "Different title"},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_validation_error_format(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={"title": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
