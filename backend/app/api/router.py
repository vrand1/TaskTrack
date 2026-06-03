from fastapi import APIRouter

from app.api.websocket import router as websocket_router
from app.domains.auth.router import router as auth_router
from app.domains.projects.router import router as projects_router
from app.domains.tasks.router import router as tasks_router
from app.domains.tasks.tag_router import router as tags_router
from app.domains.users.router import router as users_router
from app.realtime.manager import realtime_manager

router = APIRouter(prefix="/api/v1")


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/realtime", tags=["system"])
async def realtime_health() -> dict[str, int]:
    return realtime_manager.stats()


router.include_router(auth_router)
router.include_router(projects_router)
router.include_router(users_router)
router.include_router(tasks_router)
router.include_router(tags_router)
router.include_router(websocket_router)
