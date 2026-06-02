from fastapi import APIRouter, status

from app.domains.auth.dependencies import AuthServiceDep
from app.domains.auth.schemas import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(data: TokenRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.login(data)
