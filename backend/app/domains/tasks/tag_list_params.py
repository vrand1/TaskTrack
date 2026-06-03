import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TagListParams:
    q: str | None = None
    project_id: uuid.UUID | None = None
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
