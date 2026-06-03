from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.auth.dependencies import AdminUserDep, CurrentUserDep, UserStoreDep
from app.domains.tasks.api.dependencies import TaskServiceDep
from app.domains.tasks.api.router import list_query_params
from app.domains.tasks.params.list import TaskListParams
from app.domains.tasks.schemas import TaskListResponse
from app.domains.users.dependencies import UserServiceDep
from app.domains.users.schemas import (
    PasswordChangeSelf,
    PasswordResetByAdmin,
    UserCreate,
    UserRead,
    UserUpsert,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    service: UserServiceDep,
    _: AdminUserDep,
) -> UserRead:
    return await service.create(data)


@router.post("/sync", response_model=UserRead)
async def sync_user(
    data: UserUpsert,
    service: UserServiceDep,
    _: AdminUserDep,
) -> UserRead:
    return await service.sync(data)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    data: PasswordChangeSelf,
    service: UserServiceDep,
    actor: CurrentUserDep,
) -> None:
    await service.change_own_password(actor, data)


@router.post("/{email}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    email: str,
    data: PasswordResetByAdmin,
    service: UserServiceDep,
    _: AdminUserDep,
) -> None:
    await service.reset_password_by_admin(email, data)


@router.get("/{email}/tasks", response_model=TaskListResponse)
async def list_user_tasks(
    email: str,
    service: TaskServiceDep,
    users: UserStoreDep,
    _: CurrentUserDep,
    params: Annotated[TaskListParams, Depends(list_query_params)],
) -> TaskListResponse:
    await users.require_active_by_email(email)
    return await service.list_tasks(replace(params, assignee=email))


@router.get("/{email}/tasks/leaves", response_model=TaskListResponse)
async def list_user_leaf_tasks(
    email: str,
    service: TaskServiceDep,
    users: UserStoreDep,
    _: CurrentUserDep,
    params: Annotated[TaskListParams, Depends(list_query_params)],
) -> TaskListResponse:
    await users.require_active_by_email(email)
    return await service.list_tasks(replace(params, assignee=email, leaves_only=True))
