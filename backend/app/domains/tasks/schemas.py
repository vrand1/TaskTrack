import math
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.core.config import settings
from app.domains.tasks.comment_params import TaskCommentListParams
from app.domains.tasks.constants import DEFAULT_TASK_PRIORITY
from app.domains.tasks.history_params import TaskHistoryListParams
from app.domains.tasks.list_params import TaskListParams
from app.domains.tasks.models import Task
from app.domains.tasks.models.comment import TaskComment
from app.domains.tasks.models.event import TaskEvent
from app.domains.tasks.models.tag import Tag
from app.domains.tasks.refs import TaskRefRegistry
from app.domains.tasks.tag_list_params import TagListParams
from app.shared.schemas.base import APIModel
from app.shared.schemas.types import (
    AssigneeEmailStr,
    DescriptionStr,
    TaskEventType,
    TaskPriority,
    TaskStatus,
    TitleStr,
)


class TaskCreate(APIModel):
    project_id: uuid.UUID = Field()
    title: TitleStr = Field()
    assignee: AssigneeEmailStr = Field()
    parent_task_id: uuid.UUID | None = Field(
        default=None,
    )
    description: DescriptionStr | None = Field(
        default=None,
    )
    priority: TaskPriority = Field(
        default=DEFAULT_TASK_PRIORITY,
    )
    start_at: datetime | None = Field(default=None)
    end_at: datetime | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "project_id": "00000000-0000-4000-8000-000000000001",
                    "title": "Implement task API",
                    "description": "CRUD + status FSM",
                    "assignee": "admin@example.dev",
                    "priority": "high",
                }
            ]
        }
    )


class TaskUpdate(APIModel):
    title: TitleStr | None = Field(default=None)
    assignee: AssigneeEmailStr | None = Field(default=None)
    parent_task_id: uuid.UUID | None = Field(
        default=None,
    )
    description: DescriptionStr | None = Field(
        default=None,
    )
    priority: TaskPriority | None = Field(
        default=None,
    )
    start_at: datetime | None = Field(
        default=None,
    )
    end_at: datetime | None = Field(
        default=None,
    )
    tags: list[str] | None = Field(
        default=None,
    )

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Нужно передать хотя бы одно поле")
        if self.start_at is not None and self.end_at is not None and self.end_at < self.start_at:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class TaskStatusUpdate(APIModel):
    status: TaskStatus = Field(description="Целевой статус задачи.")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"status": "in_progress"}],
        }
    )


class TaskPaginationParams(APIModel):
    page: int = Field(default=1, ge=1, description="Номер страницы (начиная с 1).")
    page_size: int = Field(
        default=settings.tasks_default_page_size,
        ge=1,
        le=settings.tasks_max_page_size,
        description="Размер страницы (количество элементов).",
    )


class TaskFilterParams(APIModel):
    project_id: uuid.UUID | None = Field(default=None)
    parent_task_id: uuid.UUID | None = Field(
        default=None,
        description="ID родительской задачи; null отключает фильтр по родителю.",
    )
    root_only: bool = Field(
        default=False,
    )
    leaves_only: bool = Field(
        default=False,
    )
    status: TaskStatus | None = Field(default=None)
    assignee: AssigneeEmailStr | None = Field(default=None)
    priority: TaskPriority | None = Field(default=None)
    q: str | None = Field(
        default=None,
        max_length=255,
        description="Подстрока поиска по заголовку задачи.",
    )
    tag: str | None = Field(default=None, max_length=64)
    sort_by: Literal["created_at", "updated_at", "title", "start_at", "end_at"] = Field(
        default="created_at",
        description="Поле сортировки.",
    )
    sort_order: Literal["asc", "desc"] = Field(
        default="desc",
        description="Направление сортировки.",
    )

    def to_list_params(self, pagination: TaskPaginationParams) -> TaskListParams:
        return TaskListParams(
            project_id=self.project_id,
            parent_task_id=self.parent_task_id,
            root_only=self.root_only,
            leaves_only=self.leaves_only,
            status=self.status,
            assignee=self.assignee,
            priority=self.priority,
            q=self.q.strip() if self.q else None,
            tag=self.tag,
            sort_by=self.sort_by,
            sort_order=self.sort_order,
            page=pagination.page,
            page_size=pagination.page_size,
        )


class TaskRead(APIModel):
    id: uuid.UUID
    project_id: uuid.UUID
    parent_task_id: uuid.UUID | None
    title: str
    description: str | None
    assignee: str
    status: TaskStatus
    priority: TaskPriority
    start_at: datetime | None
    end_at: datetime | None
    was_reopened: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    subtasks: list["TaskRead"] | None = Field(
        default=None,
    )

    @classmethod
    def from_db(
        cls,
        task: Task,
        *,
        refs: TaskRefRegistry,
        subtasks: list["TaskRead"] | None = None,
    ) -> "TaskRead":
        return cls(
            id=task.id,
            project_id=task.project_id,
            parent_task_id=task.parent_task_id,
            title=task.title,
            description=task.description,
            assignee=task.assignee_user.email,
            status=refs.status_code(task.status_id),
            priority=refs.priority_code(task.priority_id),
            start_at=task.start_at,
            end_at=task.end_at,
            was_reopened=task.was_reopened,
            tags=[row.tag.name for row in task.tags],
            created_at=task.created_at,
            updated_at=task.updated_at,
            subtasks=subtasks,
        )


class PaginatedResponse(APIModel):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)

    @classmethod
    def build(
        cls,
        *,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> Self:
        pages = math.ceil(total / page_size) if total else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


class TaskListResponse(PaginatedResponse):
    items: list[TaskRead]


class TaskHistoryFilterParams(APIModel):
    event_type: TaskEventType | None = Field(default=None)
    actor: AssigneeEmailStr | None = Field(default=None)
    created_after: datetime | None = Field(
        default=None,
        description="Нижняя граница created_at (включительно).",
    )
    created_before: datetime | None = Field(
        default=None,
        description="Верхняя граница created_at (включительно).",
    )
    sort: Literal["asc", "desc"] = Field(
        default="asc",
        description="Сортировка по времени события.",
    )

    def to_list_params(
        self,
        task_id: uuid.UUID,
        pagination: TaskPaginationParams,
    ) -> TaskHistoryListParams:
        return TaskHistoryListParams(
            task_id=task_id,
            event_type=self.event_type,
            actor=self.actor,
            created_after=self.created_after,
            created_before=self.created_before,
            sort=self.sort,
            page=pagination.page,
            page_size=pagination.page_size,
        )


class TaskHistoryEntry(APIModel):
    id: uuid.UUID
    task_id: uuid.UUID
    event_type: str
    actor: str
    payload: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_db(cls, event: TaskEvent) -> Self:
        return cls(
            id=event.id,
            task_id=event.task_id,
            event_type=event.event_type,
            actor=event.actor.email,
            payload=event.payload,
            created_at=event.created_at,
        )


class TaskHistoryResponse(PaginatedResponse):
    items: list[TaskHistoryEntry]


CommentBodyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=5000),
]


class TaskCommentCreate(APIModel):
    body: CommentBodyStr = Field()


class TaskCommentRead(APIModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author: str
    body: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, comment: TaskComment) -> Self:
        return cls(
            id=comment.id,
            task_id=comment.task_id,
            author=comment.author.email,
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )


class TaskCommentFilterParams(APIModel):
    sort: Literal["asc", "desc"] = Field(
        default="asc",
        description="Сортировка комментариев по created_at.",
    )

    def to_list_params(
        self,
        task_id: uuid.UUID,
        pagination: TaskPaginationParams,
    ) -> TaskCommentListParams:
        return TaskCommentListParams(
            task_id=task_id,
            page=pagination.page,
            page_size=pagination.page_size,
            sort=self.sort,
        )


class TaskCommentListResponse(PaginatedResponse):
    items: list[TaskCommentRead]


class TagRead(APIModel):
    id: int
    name: str

    @classmethod
    def from_db(cls, tag: Tag) -> Self:
        return cls(id=tag.id, name=tag.name)


class TagFilterParams(APIModel):
    q: str | None = Field(
        default=None,
        max_length=64,
        description="Подстрока поиска по имени тега (без учёта регистра).",
    )
    project_id: uuid.UUID | None = Field(
        default=None,
        description="Если указан — только теги, используемые в активных задачах проекта.",
    )

    def to_list_params(self, pagination: TaskPaginationParams) -> TagListParams:
        return TagListParams(
            q=self.q.strip() if self.q else None,
            project_id=self.project_id,
            page=pagination.page,
            page_size=pagination.page_size,
        )


class TagListResponse(PaginatedResponse):
    items: list[TagRead]


TaskRead.model_rebuild()

