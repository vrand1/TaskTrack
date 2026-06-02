from typing import Protocol

from app.domains.users.model import User
from app.domains.users.schemas import UserCreate, UserRead, UserUpsert


class UserStore(Protocol):
    async def get_active_by_email(self, email: str) -> User | None:
        ...

    async def require_active_by_email(self, email: str) -> User:
        ...

    async def email_exists(self, email: str) -> bool:
        ...

    async def create(self, data: UserCreate) -> UserRead:
        ...

    async def upsert_by_email(self, data: UserUpsert) -> UserRead:
        ...

    async def get_by_email(self, email: str) -> User | None:
        ...

    async def update_password(self, email: str, new_password: str) -> None:
        ...
