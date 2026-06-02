from __future__ import annotations

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.exceptions import AppError
from app.db.session import resolve_session_factory
from app.domains.auth.providers.factory import build_access_token_validator, build_user_store
from app.realtime.contracts import WsCommand, build_connected_message, build_pong_message
from app.realtime.manager import realtime_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = _extract_bearer_token(websocket)
    if token is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Отсутствует Bearer-токен",
        )
        return

    validator = build_access_token_validator()
    try:
        principal = await validator.validate(token)
    except jwt.PyJWTError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Недействительный или истекший токен",
        )
        return
    except AppError as exc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=exc.message)
        return

    session_factory = resolve_session_factory(websocket.app)
    async with session_factory() as session:
        store = build_user_store(session)
        user = await store.get_active_by_email(principal.subject)
        if user is None:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Пользователь не найден или деактивирован",
            )
            return

    user_email = principal.subject
    await realtime_manager.connect(user_email=user_email, websocket=websocket)
    await websocket.send_json(build_connected_message(user=user_email))

    try:
        while True:
            command = await _read_command(websocket)
            if command.type == "ping":
                await websocket.send_json(build_pong_message())
            elif command.type == "subscribe":
                await realtime_manager.subscribe(
                    websocket=websocket,
                    project_ids=command.project_ids,
                    task_ids=command.task_ids,
                )
            elif command.type == "unsubscribe":
                await realtime_manager.unsubscribe(
                    websocket=websocket,
                    project_ids=command.project_ids,
                    task_ids=command.task_ids,
                )
            elif command.type == "ack" and command.event_id:
                await realtime_manager.ack(websocket=websocket, event_id=command.event_id)
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_manager.disconnect(user_email=user_email, websocket=websocket)


def _extract_bearer_token(websocket: WebSocket) -> str | None:
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


async def _read_command(websocket: WebSocket) -> WsCommand:
    message = await websocket.receive_text()
    if message.lower() == "ping":
        return WsCommand(type="ping")
    return WsCommand.model_validate_json(message)
