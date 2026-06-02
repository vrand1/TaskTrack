from fastapi import FastAPI

from app.api.router import router
from app.core.config import settings
from app.jobs.lifespan import app_lifespan
from app.logs import register_logging_middleware, setup_exception_handlers, setup_logging

setup_logging()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=app_lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

register_logging_middleware(app)
setup_exception_handlers(app)

app.include_router(router)
