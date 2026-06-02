from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Task Service"
    app_debug: bool = False

    log_level: str = Field(
        default="",
        description="Явный уровень логирования; пусто => выбор по app_debug.",
    )
    log_to_files: bool = Field(
        default=False,
        description="Если true, писать структурированные логи в каталог logs/.",
    )

    @property
    def effective_log_level(self) -> str:
        if self.log_level:
            return self.log_level.upper()
        return "DEBUG" if self.app_debug else "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://task_user:task_secret@localhost:5432/tasks",
        description="DSN подключения к PostgreSQL (asyncpg).",
    )
    redis_url: str = Field(
        default="redis://:redis_secret@localhost:6379/0",
        description="URL подключения к Redis.",
    )
    redis_tasks_list_ttl_seconds: int = Field(
        default=300,
        ge=1,
        description="TTL кэша списка задач, сек.",
    )
    tasks_default_page_size: int = Field(default=20, ge=1, le=100)
    tasks_max_page_size: int = Field(default=100, ge=1, le=500)

    soft_delete_retention_days: int = Field(
        default=30,
        ge=1,
        description="Срок хранения soft-deleted записей, дней.",
    )
    soft_delete_purge_interval_hours: int = Field(
        default=24,
        ge=1,
        description="Период запуска purge soft-delete, часов.",
    )

    auth_provider: Literal["local", "external"] = Field(
        default="local",
        description="Источник валидации access token.",
    )
    user_store: Literal["database", "remote"] = Field(
        default="database",
        description="Источник данных пользователей.",
    )

    jwt_secret: str = Field(default="change-me-in-env", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    grpc_enabled: bool = Field(
        default=True,
        description="Флаг запуска встроенного gRPC сервера.",
    )
    grpc_host: str = Field(default="0.0.0.0", description="Host для gRPC bind.")
    grpc_port: int = Field(default=50051, ge=1, le=65535, description="Порт gRPC сервера.")

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_async_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


settings = Settings()
