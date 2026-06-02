from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from loguru import logger

from app.realtime.contracts import WsEvent, build_event_message


class RealtimeManager:
    def __init__(self) -> None:
        self._log = logger.bind(component="realtime")
        self._by_user: dict[str, set[WebSocket]] = defaultdict(set)
        self._ws_to_user: dict[WebSocket, str] = {}
        self._ws_project_subs: dict[WebSocket, set[str]] = defaultdict(set)
        self._ws_task_subs: dict[WebSocket, set[str]] = defaultdict(set)
        self._pending_acks: dict[WebSocket, dict[str, dict[str, Any]]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._ack_retry_task: asyncio.Task | None = None
        self._ack_timeout_seconds = 5.0
        self._max_retries = 2

    async def connect(self, *, user_email: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._by_user[user_email].add(websocket)
            self._ws_to_user[websocket] = user_email
            if self._ack_retry_task is None or self._ack_retry_task.done():
                self._ack_retry_task = asyncio.create_task(self._retry_unacked_loop())
            self._log.bind(
                event="connect",
                user=user_email,
                connections=self.connection_count,
                users=len(self._by_user),
            ).info("websocket connected")

    async def disconnect(self, *, user_email: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._by_user.get(user_email)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._by_user.pop(user_email, None)
            self._ws_to_user.pop(websocket, None)
            self._ws_project_subs.pop(websocket, None)
            self._ws_task_subs.pop(websocket, None)
            self._pending_acks.pop(websocket, None)
            self._log.bind(
                event="disconnect",
                user=user_email,
                connections=self.connection_count,
                users=len(self._by_user),
            ).info("websocket disconnected")

    async def subscribe(
        self,
        *,
        websocket: WebSocket,
        project_ids: list[str],
        task_ids: list[str],
    ) -> None:
        async with self._lock:
            self._ws_project_subs[websocket].update(project_ids)
            self._ws_task_subs[websocket].update(task_ids)
            self._log.bind(
                event="subscribe",
                user=self._ws_to_user.get(websocket, "unknown"),
                project_subscriptions=len(self._ws_project_subs.get(websocket, set())),
                task_subscriptions=len(self._ws_task_subs.get(websocket, set())),
            ).debug("subscriptions updated")

    async def unsubscribe(
        self,
        *,
        websocket: WebSocket,
        project_ids: list[str],
        task_ids: list[str],
    ) -> None:
        async with self._lock:
            if websocket in self._ws_project_subs:
                self._ws_project_subs[websocket].difference_update(project_ids)
            if websocket in self._ws_task_subs:
                self._ws_task_subs[websocket].difference_update(task_ids)
            self._log.bind(
                event="unsubscribe",
                user=self._ws_to_user.get(websocket, "unknown"),
                project_subscriptions=len(self._ws_project_subs.get(websocket, set())),
                task_subscriptions=len(self._ws_task_subs.get(websocket, set())),
            ).debug("subscriptions updated")

    async def ack(self, *, websocket: WebSocket, event_id: str) -> None:
        async with self._lock:
            self._pending_acks.get(websocket, {}).pop(event_id, None)
            self._log.bind(
                event="ack",
                user=self._ws_to_user.get(websocket, "unknown"),
                event_id=event_id,
                pending_acks=self.pending_ack_count,
            ).debug("event acknowledged")

    async def send_to_user(
        self, *, user_email: str, event: WsEvent, payload: dict[str, Any]
    ) -> None:
        await self._send_many(
            sockets=list(self._by_user.get(user_email, set())),
            message=build_event_message(event=event, payload=payload),
        )

    async def broadcast(self, *, event: WsEvent, payload: dict[str, Any]) -> None:
        sockets: list[WebSocket] = []
        for user_sockets in self._by_user.values():
            sockets.extend(user_sockets)
        await self._send_many(
            sockets=sockets,
            message=build_event_message(event=event, payload=payload),
        )

    async def publish_scoped(
        self,
        *,
        event: WsEvent,
        payload: dict[str, Any],
        project_id: str | None,
        task_id: str | None,
    ) -> None:
        sockets: list[WebSocket] = []
        async with self._lock:
            for ws in self._ws_to_user:
                if self._is_subscribed(
                    websocket=ws,
                    project_id=project_id,
                    task_id=task_id,
                ):
                    sockets.append(ws)
        await self._send_many(
            sockets=sockets,
            message=build_event_message(event=event, payload=payload, requires_ack=True),
        )
        self._log.bind(
            event="publish",
            ws_event=event,
            recipients=len(sockets),
            project_id=project_id,
            task_id=task_id,
        ).info("event published")

    def _is_subscribed(
        self,
        *,
        websocket: WebSocket,
        project_id: str | None,
        task_id: str | None,
    ) -> bool:
        project_subs = self._ws_project_subs.get(websocket, set())
        task_subs = self._ws_task_subs.get(websocket, set())
        if not project_subs and not task_subs:
            return False
        if task_id and task_id in task_subs:
            return True
        if project_id and project_id in project_subs:
            return True
        return False

    async def _send_many(self, *, sockets: list[WebSocket], message: dict) -> None:
        stale: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
                if message.get("requires_ack"):
                    async with self._lock:
                        self._pending_acks[ws][message["event_id"]] = {
                            "message": message,
                            "retries": 0,
                            "last_sent": asyncio.get_running_loop().time(),
                        }
            except Exception:
                stale.append(ws)
        if stale:
            self._log.bind(event="send_stale", stale_sockets=len(stale)).warning(
                "stale sockets detected while sending"
            )
            await self._purge_stale(stale)

    async def _purge_stale(self, sockets: list[WebSocket]) -> None:
        async with self._lock:
            for ws in sockets:
                for email, user_sockets in list(self._by_user.items()):
                    if ws in user_sockets:
                        user_sockets.discard(ws)
                        if not user_sockets:
                            self._by_user.pop(email, None)
                self._ws_to_user.pop(ws, None)
                self._ws_project_subs.pop(ws, None)
                self._ws_task_subs.pop(ws, None)
                self._pending_acks.pop(ws, None)
            self._log.bind(
                event="purge",
                purged_sockets=len(sockets),
                remaining_connections=self.connection_count,
            ).warning("stale sockets purged")

    async def _retry_unacked_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            now = asyncio.get_running_loop().time()
            stale_ws: list[WebSocket] = []
            async with self._lock:
                ws_items = list(self._pending_acks.items())
            for ws, pending in ws_items:
                for event_id, item in list(pending.items()):
                    if now - item["last_sent"] < self._ack_timeout_seconds:
                        continue
                    if item["retries"] >= self._max_retries:
                        self._log.bind(
                            event="ack_timeout",
                            user=self._ws_to_user.get(ws, "unknown"),
                            event_id=event_id,
                            retries=item["retries"],
                        ).warning("ack timeout reached, dropping socket")
                        stale_ws.append(ws)
                        break
                    try:
                        await ws.send_json(item["message"])
                        async with self._lock:
                            if event_id in self._pending_acks.get(ws, {}):
                                self._pending_acks[ws][event_id]["retries"] += 1
                                self._pending_acks[ws][event_id]["last_sent"] = now
                        self._log.bind(
                            event="retry",
                            user=self._ws_to_user.get(ws, "unknown"),
                            event_id=event_id,
                            retry=item["retries"] + 1,
                        ).debug("resending unacked event")
                    except Exception:
                        stale_ws.append(ws)
                        break
            if stale_ws:
                await self._purge_stale(stale_ws)

    @property
    def connection_count(self) -> int:
        return len(self._ws_to_user)

    @property
    def pending_ack_count(self) -> int:
        return sum(len(items) for items in self._pending_acks.values())

    def stats(self) -> dict[str, int]:
        return {
            "connections": self.connection_count,
            "users": len(self._by_user),
            "project_subscriptions": sum(len(items) for items in self._ws_project_subs.values()),
            "task_subscriptions": sum(len(items) for items in self._ws_task_subs.values()),
            "pending_acks": self.pending_ack_count,
        }


realtime_manager = RealtimeManager()
