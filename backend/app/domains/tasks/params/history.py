import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.shared.query.pagination import OffsetPagination


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskHistoryListParams(OffsetPagination):
    task_id: uuid.UUID
    event_type: str | None = None
    actor: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    sort: Literal["asc", "desc"] = "asc"
