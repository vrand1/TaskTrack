import uuid
from datetime import datetime
from typing import Self

from pydantic import Field, field_validator, model_validator

from app.core.config import settings
from app.domains.projects.model import Project
from app.shared.schemas.base import APIModel
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.schemas.types import DescriptionStr, TitleStr


class ProjectCreate(APIModel):
    name: TitleStr = Field(description="Название проекта")
    slug: str | None = Field(
        default=None,
        max_length=64,
    )
    description: DescriptionStr | None = None


class ProjectUpdate(APIModel):
    name: TitleStr | None = None
    slug: str | None = Field(default=None, max_length=64)
    description: DescriptionStr | None = None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Нужно передать хотя бы одно поле")
        return self


class ProjectRead(APIModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, project: Project) -> Self:
        return cls(
            id=project.id,
            slug=project.slug,
            name=project.name,
            description=project.description,
            created_by=project.created_by.email,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectPaginationParams(APIModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=settings.tasks_default_page_size,
        ge=1,
        le=settings.tasks_max_page_size,
    )


class ProjectListResponse(PaginatedResponse):
    items: list[ProjectRead]
