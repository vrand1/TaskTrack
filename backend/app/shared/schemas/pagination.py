import math
from typing import Any, Self

from pydantic import Field

from app.shared.schemas.base import APIModel


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
