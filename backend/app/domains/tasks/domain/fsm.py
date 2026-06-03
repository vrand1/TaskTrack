from app.core.exceptions import InvalidStatusTransitionError


def validate_status_transition(
    current: str,
    new: str,
    *,
    ordered_codes: list[str],
) -> None:
    """Переходы по sort_order справочника, не по id статуса."""
    if current == new:
        return

    if current not in ordered_codes or new not in ordered_codes:
        raise InvalidStatusTransitionError(
            f"Неизвестный статус в переходе: '{current}' -> '{new}'."
        )

    terminal = ordered_codes[-1]
    if current == terminal:
        raise InvalidStatusTransitionError(
            "Нельзя изменить статус: задача уже в финальном состоянии. "
            "Для переоткрытия используйте POST /api/v1/tasks/{task_id}/reopen."
        )

    current_idx = ordered_codes.index(current)
    new_idx = ordered_codes.index(new)

    if new_idx < current_idx:
        return

    if new_idx == current_idx + 1:
        return

    if new_idx > current_idx + 1:
        raise InvalidStatusTransitionError(
            f"Нельзя пропускать статусы: следующий допустимый шаг из '{current}' "
            f"— '{ordered_codes[current_idx + 1]}'."
        )

    raise InvalidStatusTransitionError(f"Переход из '{current}' в '{new}' запрещен.")
