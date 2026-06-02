from __future__ import annotations

import grpc

from app.core.config import settings

from .auth import AuthInterceptor
from .generated import task_service_pb2_grpc as pb2_grpc
from .services import ProjectGrpcService, SystemGrpcService, TaskGrpcService


class GrpcServer:
    def __init__(self) -> None:
        self._server = grpc.aio.server(
            interceptors=(
                AuthInterceptor(public_methods={"/task.v1.SystemService/Health"}),
            )
        )
        pb2_grpc.add_SystemServiceServicer_to_server(SystemGrpcService(), self._server)
        pb2_grpc.add_ProjectServiceServicer_to_server(ProjectGrpcService(), self._server)
        pb2_grpc.add_TaskServiceServicer_to_server(TaskGrpcService(), self._server)
        self._server.add_insecure_port(f"{settings.grpc_host}:{settings.grpc_port}")

    async def start(self) -> None:
        await self._server.start()

    async def stop(self, grace_seconds: int = 5) -> None:
        await self._server.stop(grace_seconds)
