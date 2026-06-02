import pytest
from starlette.testclient import TestClient

from app.main import app
from tests.users import AdminUser


@pytest.mark.usefixtures("client")
@pytest.mark.asyncio
async def test_websocket_connect(auth_headers: dict[str, str]) -> None:
    with TestClient(app) as tc:
        with tc.websocket_connect("/api/v1/ws", headers=auth_headers) as ws:
            message = ws.receive_json()
            assert message["event"] == "connected"
            assert message["payload"]["user"] == AdminUser.email

            ws.send_text("ping")
            pong = ws.receive_json()
            assert pong["event"] == "pong"
