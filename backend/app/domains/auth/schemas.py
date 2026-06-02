from pydantic import Field

from app.shared.schemas.base import APIModel
from app.shared.schemas.types import AssigneeEmailStr


class TokenRequest(APIModel):
    email: AssigneeEmailStr = Field(description="Логин пользователя (email).")
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Время жизни access token, сек.")
