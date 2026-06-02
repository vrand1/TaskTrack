from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from app.shared.schemas.base import APIModel
from app.shared.schemas.types import AssigneeEmailStr

if TYPE_CHECKING:
    from app.domains.users.model import User


class UserCreate(APIModel):
    email: AssigneeEmailStr
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True
    is_admin: bool = Field(
        default=False,
    )


class PasswordChangeSelf(APIModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetByAdmin(APIModel):
    new_password: str = Field(min_length=8, max_length=128)


class UserUpsert(APIModel):

    email: AssigneeEmailStr
    is_active: bool = True
    is_admin: bool = False


class UserRead(APIModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    @classmethod
    def from_db(cls, user: "User") -> "UserRead":
        return cls(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )
