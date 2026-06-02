from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.dependencies import SessionDep
from app.core.exceptions import AppError, ForbiddenError, UnauthorizedError
from app.domains.auth.ports import (
    AccessTokenValidator,
    AuthenticatedPrincipal,
)
from app.domains.auth.providers.factory import (
    build_access_token_validator,
    build_credential_authenticator,
    build_user_store,
)
from app.domains.auth.service import AuthService
from app.domains.users.model import User
from app.domains.users.ports import UserStore

http_bearer = HTTPBearer(auto_error=False)


def get_access_token_validator() -> AccessTokenValidator:
    return build_access_token_validator()


def get_user_store(session: SessionDep) -> UserStore:
    return build_user_store(session)


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(build_credential_authenticator(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
AccessTokenValidatorDep = Annotated[AccessTokenValidator, Depends(get_access_token_validator)]
UserStoreDep = Annotated[UserStore, Depends(get_user_store)]


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    validator: AccessTokenValidatorDep,
) -> AuthenticatedPrincipal:
    if credentials is None:
        raise UnauthorizedError()
    try:
        return await validator.validate(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Недействительный или истекший токен") from exc
    except AppError as exc:
        if exc.status_code == 501:
            raise UnauthorizedError(exc.message) from exc
        raise

CurrentPrincipalDep = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]

async def get_current_user(
    principal: CurrentPrincipalDep,
    store: UserStoreDep,
) -> User:
    user = await store.get_active_by_email(principal.subject)
    if user is None:
        raise UnauthorizedError("Пользователь не найден или деактивирован")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _is_admin(principal: AuthenticatedPrincipal, user: User) -> bool:
    if principal.is_admin is not None:
        return principal.is_admin
    return user.is_admin


async def get_current_admin_user(
    user: CurrentUserDep,
    principal: CurrentPrincipalDep,
) -> User:
    if not _is_admin(principal, user):
        raise ForbiddenError()
    return user


AdminUserDep = Annotated[User, Depends(get_current_admin_user)]
