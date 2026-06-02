import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get("/api/v1/tasks", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers.get("x-request-id")


@pytest.mark.asyncio
async def test_app_error_includes_request_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Task",
            "assignee": "nobody@example.dev",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "UNKNOWN_ASSIGNEE"
    assert "request_id" in body
