import uuid
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TaskListParams:
    project_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    root_only: bool = False
    leaves_only: bool = False
    status: str | None = None
    assignee: str | None = None
    priority: str | None = None
    q: str | None = None
    tag: str | None = None
    sort_by: Literal["created_at", "updated_at", "title", "start_at", "end_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
