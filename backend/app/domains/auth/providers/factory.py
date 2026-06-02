from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.domains.auth.ports import AccessTokenValidator, CredentialAuthenticator, PasswordResetter
from app.domains.auth.providers.local_jwt import (
    LocalCredentialAuthenticator,
    LocalJwtAccessTokenValidator,
    LocalPasswordResetter,
)
from app.domains.users.adapters.remote import RemoteUserStore
from app.domains.users.adapters.sqlalchemy import SqlAlchemyUserStore
from app.domains.users.ports import UserStore


@lru_cache
def build_access_token_validator() -> AccessTokenValidator:
    if settings.auth_provider == "local":
        return LocalJwtAccessTokenValidator()
    raise AppError(
        code="AUTH_PROVIDER_NOT_CONFIGURED",
        message=(
            "AUTH_PROVIDER=external: добавьте класс AccessTokenValidator "
            "(OIDC/JWKS, корпоративный IdP) в auth/providers/ и подключите здесь."
        ),
        status_code=501,
    )


def build_user_store(session: AsyncSession) -> UserStore:
    if settings.user_store == "database":
        return SqlAlchemyUserStore(session)
    return RemoteUserStore()


def build_credential_authenticator(session: AsyncSession) -> CredentialAuthenticator | None:
    if settings.auth_provider == "local":
        return LocalCredentialAuthenticator(build_user_store(session))
    return None


def build_password_resetter(session: AsyncSession) -> PasswordResetter | None:
    if settings.auth_provider == "local":
        return LocalPasswordResetter(build_user_store(session))
    return None
