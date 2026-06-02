from app.core.exceptions import AppError
from app.domains.auth.ports import PasswordResetter
from app.domains.users.model import User
from app.domains.users.ports import UserStore
from app.domains.users.schemas import (
    PasswordChangeSelf,
    PasswordResetByAdmin,
    UserCreate,
    UserRead,
    UserUpsert,
)


class UserService:
    def __init__(
        self,
        users: UserStore,
        password_reset: PasswordResetter | None = None,
    ) -> None:
        self._users = users
        self._password_reset = password_reset

    async def create(self, data: UserCreate) -> UserRead:
        return await self._users.create(data)

    async def sync(self, data: UserUpsert) -> UserRead:
        return await self._users.upsert_by_email(data)

    async def change_own_password(self, actor: User, data: PasswordChangeSelf) -> None:
        resetter = self._require_password_reset()
        await resetter.change_own(actor.email, data.current_password, data.new_password)

    async def reset_password_by_admin(self, email: str, data: PasswordResetByAdmin) -> None:
        resetter = self._require_password_reset()
        await resetter.reset_for_user(email, data.new_password)

    def _require_password_reset(self) -> PasswordResetter:
        if self._password_reset is None:
            raise AppError(
                code="EXTERNAL_AUTH_PROVIDER",
                message=(
                    "Сброс пароля через этот API отключен (AUTH_PROVIDER=external). "
                    "Меняйте пароль во внешнем IdP/LDAP."
                ),
                status_code=501,
            )
        return self._password_reset
