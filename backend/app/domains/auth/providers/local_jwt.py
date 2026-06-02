import jwt

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    UserNotFoundError,
)
from app.core.security import create_access_token, decode_access_token, verify_password
from app.domains.auth.ports import (
    AuthenticatedPrincipal,
)
from app.domains.auth.schemas import TokenResponse
from app.domains.users.ports import UserStore


class LocalJwtAccessTokenValidator:
    async def validate(self, token: str) -> AuthenticatedPrincipal:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not isinstance(email, str) or not email:
            raise jwt.InvalidTokenError("Missing sub claim")
        return AuthenticatedPrincipal(subject=email, is_admin=None)


class LocalCredentialAuthenticator:
    def __init__(self, users: UserStore) -> None:
        self._users = users

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._users.get_active_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        token = create_access_token(user.email)
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_expire_minutes * 60,
        )


class LocalPasswordResetter:
    def __init__(self, users: UserStore) -> None:
        self._users = users

    async def change_own(self, email: str, current_password: str, new_password: str) -> None:
        user = await self._users.get_active_by_email(email)
        if user is None or not verify_password(current_password, user.password_hash):
            raise InvalidCurrentPasswordError()
        await self._users.update_password(email, new_password)

    async def reset_for_user(self, email: str, new_password: str) -> None:
        user = await self._users.get_by_email(email)
        if user is None:
            raise UserNotFoundError(email)
        await self._users.update_password(email, new_password)
