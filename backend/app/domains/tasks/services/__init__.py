__all__ = ["TaskService"]


def __getattr__(name: str):
    if name == "TaskService":
        from app.domains.tasks.services.task import TaskService

        return TaskService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
