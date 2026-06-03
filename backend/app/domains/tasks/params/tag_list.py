import uuid
from dataclasses import dataclass

from app.shared.query.pagination import OffsetPagination


@dataclass(frozen=True, slots=True, kw_only=True)
class TagListParams(OffsetPagination):
    q: str | None = None
    project_id: uuid.UUID | None = None
