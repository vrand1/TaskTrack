import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class TaskHistoryListParams:
    task_id: uuid.UUID
    event_type: str | None = None
    actor: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    sort: Literal["asc", "desc"] = "asc"
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
