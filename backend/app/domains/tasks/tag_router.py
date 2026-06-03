from typing import Annotated

from fastapi import APIRouter, Depends

from app.domains.auth.dependencies import CurrentUserDep
from app.domains.tasks.dependencies import TaskServiceDep
from app.domains.tasks.schemas import (
    TagFilterParams,
    TagListResponse,
    TaskPaginationParams,
)
from app.domains.tasks.tag_list_params import TagListParams

router = APIRouter(prefix="/tags", tags=["tags"])


def tag_list_query_params(
    filters: Annotated[TagFilterParams, Depends()],
    pagination: Annotated[TaskPaginationParams, Depends()],
) -> TagListParams:
    return filters.to_list_params(pagination)


@router.get("", response_model=TagListResponse)
async def list_tags(
    service: TaskServiceDep,
    _: CurrentUserDep,
    params: Annotated[TagListParams, Depends(tag_list_query_params)],
) -> TagListResponse:
    return await service.list_tags(params)
