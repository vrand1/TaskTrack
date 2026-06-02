import asyncio
import socket
import uuid

import grpc
import pytest
from google.protobuf.empty_pb2 import Empty
from httpx import AsyncClient

from app.core.config import settings
from app.grpc import services as grpc_services
from app.grpc.generated import task_service_pb2 as pb2
from app.grpc.generated import task_service_pb2_grpc as pb2_grpc
from app.grpc.server import GrpcServer
from app.main import app


async def _grpc_channel(port: int) -> grpc.aio.Channel:
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    await asyncio.wait_for(channel.channel_ready(), timeout=5)
    return channel


@pytest.fixture(autouse=True)
async def grpc_server(fake_redis, client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    monkeypatch.setattr(settings, "grpc_host", "127.0.0.1")
    monkeypatch.setattr(settings, "grpc_port", port)
    grpc_services.async_session_factory = app.state.test_session_factory
    grpc_services.get_redis = lambda: fake_redis
    server = GrpcServer()
    await server.start()
    try:
        yield port
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_grpc_health(grpc_server: int) -> None:
    channel = await _grpc_channel(grpc_server)
    try:
        stub = pb2_grpc.SystemServiceStub(channel)
        response = await stub.Health(Empty())
        assert response.status == "ok"
    finally:
        await channel.close()


@pytest.mark.asyncio
async def test_grpc_list_projects_requires_auth(grpc_server: int) -> None:
    channel = await _grpc_channel(grpc_server)
    try:
        stub = pb2_grpc.ProjectServiceStub(channel)
        with pytest.raises(grpc.aio.AioRpcError) as exc:
            await stub.ListProjects(Empty())
        assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED
    finally:
        await channel.close()


@pytest.mark.asyncio
async def test_grpc_create_and_list_tasks(
    grpc_server: int,
    auth_headers: dict[str, str],
    project_id: str,
) -> None:
    channel = await _grpc_channel(grpc_server)
    try:
        task_stub = pb2_grpc.TaskServiceStub(channel)
        metadata = (("authorization", auth_headers["Authorization"]),)
        title = f"gRPC task {uuid.uuid4().hex[:8]}"

        create_response = await task_stub.CreateTask(
            pb2.CreateTaskRequest(
                project_id=project_id,
                title=title,
                assignee="admin@example.dev",
                tags=["grpc", "test"],
            ),
            metadata=metadata,
        )
        assert create_response.id
        assert create_response.project_id == project_id
        assert create_response.status == "todo"
        assert create_response.title == title

        list_response = await task_stub.ListTasks(
            pb2.ListTasksRequest(project_id=project_id, page=1, page_size=50),
            metadata=metadata,
        )
        assert list_response.total >= 1
        assert any(item.id == create_response.id for item in list_response.items)
    finally:
        await channel.close()


