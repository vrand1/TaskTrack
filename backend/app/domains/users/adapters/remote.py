
from app.core.exceptions import AppError
from app.domains.users.model import User
from app.domains.users.schemas import UserCreate, UserRead, UserUpsert


class RemoteUserStore:
    async def get_active_by_email(self, email: str) -> User | None:
        raise self._not_configured()

    async def require_active_by_email(self, email: str) -> User:
        raise self._not_configured()

    async def email_exists(self, email: str) -> bool:
        raise self._not_configured()

    async def create(self, data: UserCreate) -> UserRead:
        raise self._not_configured()

    async def upsert_by_email(self, data: UserUpsert) -> UserRead:
        raise self._not_configured()

    async def get_by_email(self, email: str) -> User | None:
        raise self._not_configured()

    async def update_password(self, email: str, new_password: str) -> None:
        raise self._not_configured()

    def _not_configured(self) -> AppError:
        return AppError(
            code="USER_STORE_NOT_CONFIGURED",
            message="Внешний сервис пользователей: не реализован контракт",
            status_code=501,
        )
