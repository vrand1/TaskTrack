from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class OffsetPagination:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
