
from dataclasses import dataclass
from typing import Protocol

from app.domains.auth.schemas import TokenResponse


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    subject: str
    is_admin: bool | None = None


class AccessTokenValidator(Protocol):
    async def validate(self, token: str) -> AuthenticatedPrincipal:
        ...


class CredentialAuthenticator(Protocol):

    async def login(self, email: str, password: str) -> TokenResponse:
        ...


class PasswordResetter(Protocol):

    async def change_own(self, email: str, current_password: str, new_password: str) -> None:
        ...

    async def reset_for_user(self, email: str, new_password: str) -> None:
        ...
