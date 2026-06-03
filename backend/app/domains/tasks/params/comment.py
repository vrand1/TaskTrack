import uuid
from dataclasses import dataclass
from typing import Literal

from app.shared.query.pagination import OffsetPagination


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCommentListParams(OffsetPagination):
    task_id: uuid.UUID
    sort: Literal["asc", "desc"] = "asc"
