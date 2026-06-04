from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field, StringConstraints

from app.domains.tasks.domain.constants import TASK_EVENT_TYPES, TASK_PRIORITIES, TASK_STATUSES

TitleStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

AssigneeEmailStr = Annotated[
    EmailStr,
    Field(max_length=255),
]

DescriptionStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=10_000),
]


# Валидация по constants, не по живому справочнику из БД — см. domains/tasks/domain/constants.py.
def _validate_task_status(value: str) -> str:
    if value not in TASK_STATUSES: # TODO вынести в динамику
        allowed = ", ".join(TASK_STATUSES)
        raise ValueError(f"Некорректный статус '{value}'. Допустимые значения: {allowed}")
    return value


# Аналогично статусам: приоритеты в API синхронизированы через constants.
def _validate_task_priority(value: str) -> str:
    if value not in TASK_PRIORITIES: # TODO вынести в динамику
        allowed = ", ".join(TASK_PRIORITIES)
        raise ValueError(f"Некорректный приоритет '{value}'. Допустимые значения: {allowed}")
    return value


TaskStatus = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    AfterValidator(_validate_task_status),
    Field(json_schema_extra={"enum": list(TASK_STATUSES)}),
]

TaskPriority = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    AfterValidator(_validate_task_priority),
    Field(json_schema_extra={"enum": list(TASK_PRIORITIES)}),
]


def _validate_task_event_type(value: str) -> str:
    if value not in TASK_EVENT_TYPES:
        allowed = ", ".join(TASK_EVENT_TYPES)
        raise ValueError(f"Некорректный event_type '{value}'. Допустимые значения: {allowed}")
    return value


TaskEventType = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    AfterValidator(_validate_task_event_type),
    Field(json_schema_extra={"enum": list(TASK_EVENT_TYPES)}),
]
