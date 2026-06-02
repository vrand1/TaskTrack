import pytest

from app.core.exceptions import InvalidStatusTransitionError
from app.domains.tasks.constants import TASK_STATUSES
from app.domains.tasks.fsm import validate_status_transition

ORDERED = list(TASK_STATUSES)


def test_cannot_leave_done() -> None:
    with pytest.raises(InvalidStatusTransitionError, match="финальном состоянии"):
        validate_status_transition("done", "review", ordered_codes=ORDERED)


def test_cannot_reopen_from_done_via_fsm() -> None:
    with pytest.raises(InvalidStatusTransitionError, match="финальном состоянии"):
        validate_status_transition("done", "todo", ordered_codes=ORDERED)


def test_forward_step() -> None:
    validate_status_transition("todo", "in_progress", ordered_codes=ORDERED)


def test_cannot_skip_status() -> None:
    with pytest.raises(InvalidStatusTransitionError, match="Нельзя пропускать статусы"):
        validate_status_transition("todo", "done", ordered_codes=ORDERED)


def test_backward_allowed_before_done() -> None:
    validate_status_transition("review", "in_progress", ordered_codes=ORDERED)
