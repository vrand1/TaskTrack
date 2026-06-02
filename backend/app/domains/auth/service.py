from app.core.exceptions import AppError
from app.domains.auth.ports import CredentialAuthenticator
from app.domains.auth.schemas import TokenRequest, TokenResponse


class AuthService:
    def __init__(self, credential_auth: CredentialAuthenticator | None) -> None:
        self._credential_auth = credential_auth

    async def login(self, data: TokenRequest) -> TokenResponse:
        if self._credential_auth is None:
            raise AppError(
                code="EXTERNAL_AUTH_PROVIDER",
                message=(
                    "Логин через этот API отключен (AUTH_PROVIDER=external). "
                    "Аутентификация выполняется во внешнем IdP/LDAP, "
                    "получите Bearer-токен там."
                ),
                status_code=501,
            )
        return await self._credential_auth.login(data.email, data.password)
