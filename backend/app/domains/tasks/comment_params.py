import uuid
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TaskCommentListParams:
    task_id: uuid.UUID
    page: int = 1
    page_size: int = 20
    sort: Literal["asc", "desc"] = "asc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
