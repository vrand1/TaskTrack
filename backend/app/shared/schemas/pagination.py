import math
from typing import Any, Self

from pydantic import Field

from app.core.config import settings
from app.shared.query.pagination import OffsetPagination
from app.shared.schemas.base import APIModel


class PaginationParams(APIModel):
    page: int = Field(default=1, ge=1, description="Номер страницы (начиная с 1).")
    page_size: int = Field(
        default=settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Размер страницы (количество элементов).",
    )

    def to_offset(self) -> OffsetPagination:
        return OffsetPagination(page=self.page, page_size=self.page_size)


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
