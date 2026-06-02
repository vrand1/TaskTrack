import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailTakenError, UnknownAssigneeError, UserNotFoundError
from app.core.security import hash_password
from app.domains.users.model import User
from app.domains.users.schemas import UserCreate, UserRead, UserUpsert


class SqlAlchemyUserStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def _get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def require_active_by_email(self, email: str) -> User:
        user = await self.get_active_by_email(email)
        if user is None:
            raise UnknownAssigneeError(email)
        return user

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(
            select(User.id).where(User.email == email).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def create(self, data: UserCreate) -> UserRead:
        if await self.email_exists(data.email):
            raise EmailTakenError(data.email)

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            is_active=data.is_active,
            is_admin=data.is_admin,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return UserRead.from_db(user)

    async def upsert_by_email(self, data: UserUpsert) -> UserRead:
        existing = await self._get_by_email(data.email)
        if existing is None:
            user = User(
                email=data.email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                is_active=data.is_active,
                is_admin=data.is_admin,
            )
            self._session.add(user)
            await self._session.flush()
            await self._session.refresh(user)
            return UserRead.from_db(user)

        existing.is_active = data.is_active
        existing.is_admin = data.is_admin
        await self._session.flush()
        await self._session.refresh(existing)
        return UserRead.from_db(existing)

    async def get_by_email(self, email: str) -> User | None:
        return await self._get_by_email(email)

    async def update_password(self, email: str, new_password: str) -> None:
        user = await self._get_by_email(email)
        if user is None:
            raise UserNotFoundError(email)
        user.password_hash = hash_password(new_password)
        await self._session.flush()
