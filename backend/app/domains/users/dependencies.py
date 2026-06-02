from typing import Annotated

from fastapi import Depends

from app.api.dependencies import SessionDep
from app.domains.auth.dependencies import UserStoreDep
from app.domains.auth.providers.factory import build_password_resetter
from app.domains.users.service import UserService


def get_user_service(store: UserStoreDep, session: SessionDep) -> UserService:
    return UserService(store, build_password_resetter(session))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
