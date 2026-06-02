from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError


@dataclass(frozen=True, slots=True)
class StatusRef:
    id: int
    code: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class PriorityRef:
    id: int
    code: str


class TaskRefRegistry:
    def __init__(
        self,
        statuses: list[StatusRef],
        priorities: list[PriorityRef],
    ) -> None:
        if not statuses:
            raise ValueError("Справочник статусов задач пуст")
        if not priorities:
            raise ValueError("Справочник приоритетов задач пуст")

        self._statuses_by_id = {row.id: row for row in statuses}
        self._statuses_by_code = {row.code: row for row in statuses}
        self._priorities_by_id = {row.id: row for row in priorities}
        self._priorities_by_code = {row.code: row for row in priorities}
        self._status_order = [
            row.code for row in sorted(statuses, key=lambda item: item.sort_order)
        ]

    def ordered_status_codes(self) -> list[str]:
        return list(self._status_order)

    def terminal_status_code(self) -> str:
        return self._status_order[-1]

    def status_code(self, status_id: int) -> str:
        try:
            return self._statuses_by_id[status_id].code
        except KeyError as exc:
            raise AppError(
                code="UNKNOWN_STATUS_ID",
                message=f"Статус с id {status_id} не настроен",
                status_code=500,
            ) from exc

    def status_id(self, code: str) -> int:
        row = self._statuses_by_code.get(code)
        if row is None:
            raise AppError(
                code="UNKNOWN_STATUS",
                message=f"Статус '{code}' не настроен",
                status_code=400,
            )
        return row.id

    def priority_code(self, priority_id: int) -> str:
        try:
            return self._priorities_by_id[priority_id].code
        except KeyError as exc:
            raise AppError(
                code="UNKNOWN_PRIORITY_ID",
                message=f"Приоритет с id {priority_id} не настроен",
                status_code=500,
            ) from exc

    def priority_id(self, code: str) -> int:
        row = self._priorities_by_code.get(code)
        if row is None:
            raise AppError(
                code="UNKNOWN_PRIORITY",
                message=f"Приоритет '{code}' не настроен",
                status_code=400,
            )
        return row.id


_registry: TaskRefRegistry | None = None


def get_task_ref_registry() -> TaskRefRegistry:
    if _registry is None:
        raise RuntimeError(
            "Реестр справочников задач не загружен; сначала вызовите init_task_ref_registry()"
        )
    return _registry


async def init_task_ref_registry(session: AsyncSession) -> TaskRefRegistry:
    from app.domains.tasks.ref_repository import TaskRefRepository

    global _registry
    loader = TaskRefRepository(session)
    statuses = await loader.load_statuses()
    priorities = await loader.load_priorities()
    _registry = TaskRefRegistry(statuses, priorities)
    return _registry


async def reload_task_ref_registry(session: AsyncSession) -> TaskRefRegistry:
    return await init_task_ref_registry(session)


def reset_task_ref_registry_for_tests() -> None:
    global _registry
    _registry = None
