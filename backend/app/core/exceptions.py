from dataclasses import dataclass


@dataclass(eq=False)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Требуется аутентификация") -> None:
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Требуются права администратора") -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Неверный email или пароль",
            status_code=401,
        )


class InvalidCurrentPasswordError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CURRENT_PASSWORD",
            message="Текущий пароль указан неверно",
            status_code=401,
        )


class UserNotFoundError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(
            code="USER_NOT_FOUND",
            message=f"Пользователь с email '{email}' не найден",
            status_code=404,
        )


class TaskNotFoundError(AppError):
    def __init__(self, task_id: str) -> None:
        super().__init__(
            code="TASK_NOT_FOUND",
            message=f"Задача {task_id} не найдена",
            status_code=404,
        )


class ProjectNotFoundError(AppError):
    def __init__(self, project_id: str) -> None:
        super().__init__(
            code="PROJECT_NOT_FOUND",
            message=f"Проект {project_id} не найден",
            status_code=404,
        )


class InvalidProjectSlugError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_PROJECT_SLUG",
            message=(
                "Нельзя построить slug: используйте латиницу, цифры, дефис "
                "(или укажите поле slug явно)."
            ),
            status_code=422,
        )


class ProjectSlugTakenError(AppError):
    def __init__(self, slug: str) -> None:
        super().__init__(
            code="PROJECT_SLUG_TAKEN",
            message=f"Slug проекта '{slug}' уже занят",
            status_code=409,
        )


class InvalidParentTaskError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(code="INVALID_PARENT_TASK", message=message, status_code=400)


class InvalidStatusTransitionError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="INVALID_STATUS_TRANSITION",
            message=message,
            status_code=409,
        )


class TaskNotReopenableError(AppError):
    def __init__(self, *, current_status: str, terminal_status: str) -> None:
        super().__init__(
            code="TASK_NOT_REOPENABLE",
            message=(
                f"Переоткрытие доступно только для задач в статусе '{terminal_status}'. "
                f"Текущий статус: '{current_status}'."
            ),
            status_code=409,
        )


class TaskAlreadyReopenedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="TASK_ALREADY_REOPENED",
            message="Задачу можно переоткрыть только один раз.",
            status_code=409,
        )


class EmailTakenError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(
            code="EMAIL_TAKEN",
            message=f"Email '{email}' уже занят",
            status_code=409,
        )


class UnknownAssigneeError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(
            code="UNKNOWN_ASSIGNEE",
            message=f"Пользователь с email '{email}' не найден",
            status_code=400,
        )


class IdempotencyConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="IDEMPOTENCY_CONFLICT",
            message="Ключ Idempotency-Key уже использован с другим телом запроса",
            status_code=409,
        )


class RestoreExpiredError(AppError):
    def __init__(self, *, entity: str, retention_days: int) -> None:
        super().__init__(
            code="RESTORE_EXPIRED",
            message=(
                f"{entity} был удален более {retention_days} дней назад "
                "и больше не может быть восстановлен"
            ),
            status_code=410,
        )
