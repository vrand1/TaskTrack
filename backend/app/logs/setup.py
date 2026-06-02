import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings

_configured = False

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


def _console_filter(record: dict) -> bool:
    return record["extra"].get("sink", "both") in ("console", "both")


def _file_filter(record: dict) -> bool:
    return record["extra"].get("sink", "both") in ("file", "both")


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    logger.remove()

    fmt = LOG_FORMAT
    if settings.app_debug:
        fmt += " | <magenta>{extra}</magenta>"

    logger.add(
        sys.stdout,
        format=fmt,
        level=settings.effective_log_level,
        colorize=True,
        filter=_console_filter,
    )

    if settings.log_to_files:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        logger.add(
            logs_dir / "app.log",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            serialize=True,
            filter=_file_filter,
        )
        logger.add(
            logs_dir / "errors.log",
            level="ERROR",
            rotation="20 MB",
            retention="90 days",
            serialize=True,
            filter=_file_filter,
        )

    _configured = True
