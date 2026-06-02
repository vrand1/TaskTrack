from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from app.shared.schemas.base import APIModel

WsEvent = Literal[
    "connected",
    "pong",
    "task_created",
    "task_updated",
    "task_status_changed",
    "task_deleted",
    "task_restored",
    "task_comment_added",
]
WsCommandType = Literal["ping", "subscribe", "unsubscribe", "ack"]


class WsEnvelope(APIModel):
    event_id: str
    event: WsEvent
    payload: dict[str, Any]
    requires_ack: bool = False


class WsConnectedPayload(APIModel):
    user: str


class WsPongPayload(APIModel):
    pass


class WsCommand(APIModel):
    type: WsCommandType
    project_ids: list[str] = []
    task_ids: list[str] = []
    event_id: str | None = None


class TaskCreatedPayload(APIModel):
    task_id: str
    project_id: str
    actor: str
    assignee: str
    status: str
    priority: str
    was_reopened: bool


class TaskUpdatedPayload(APIModel):
    task_id: str
    project_id: str
    actor: str
    assignee: str
    changes: list[dict[str, Any]]


class TaskStatusChangedPayload(APIModel):
    task_id: str
    project_id: str
    actor: str
    assignee: str
    from_status: str
    to_status: str
    reopened: bool


class TaskDeletedPayload(APIModel):
    task_id: str
    project_id: str
    actor: str


class TaskRestoredPayload(APIModel):
    task_id: str
    project_id: str
    actor: str
    assignee: str


class TaskCommentAddedPayload(APIModel):
    task_id: str
    project_id: str
    comment_id: str
    actor: str
    body: str


def build_connected_message(*, user: str) -> dict[str, Any]:
    return WsEnvelope(
        event_id=uuid4().hex,
        event="connected",
        payload=WsConnectedPayload(user=user).model_dump(),
    ).model_dump()


def build_pong_message() -> dict[str, Any]:
    return WsEnvelope(
        event_id=uuid4().hex,
        event="pong",
        payload=WsPongPayload().model_dump(),
    ).model_dump()


def build_event_message(
    *,
    event: WsEvent,
    payload: dict[str, Any],
    requires_ack: bool = True,
) -> dict[str, Any]:
    return WsEnvelope(
        event_id=uuid4().hex,
        event=event,
        payload=payload,
        requires_ack=requires_ack,
    ).model_dump()
