import pytest

from app.core.exceptions import InvalidStatusTransitionError
from app.domains.tasks.domain.constants import TASK_PRIORITIES, TASK_STATUSES
from app.domains.tasks.domain.fsm import validate_status_transition
from app.domains.tasks.domain.refs import PriorityRef, StatusRef, TaskRefRegistry


def _default_registry() -> TaskRefRegistry:
    statuses = [
        StatusRef(id=index + 1, code=code, sort_order=index + 1)
        for index, code in enumerate(TASK_STATUSES)
    ]
    priorities = [
        PriorityRef(id=index + 1, code=code) for index, code in enumerate(TASK_PRIORITIES)
    ]
    return TaskRefRegistry(statuses, priorities)


def test_registry_code_id_roundtrip() -> None:
    refs = _default_registry()
    assert refs.status_code(1) == "todo"
    assert refs.status_id("done") == 4
    assert refs.priority_code(2) == "medium"


def test_fsm_uses_sort_order_not_id_gaps() -> None:
    statuses = [
        StatusRef(id=1, code="todo", sort_order=1),
        StatusRef(id=2, code="in_progress", sort_order=2),
        StatusRef(id=10, code="review", sort_order=3),
        StatusRef(id=4, code="done", sort_order=4),
    ]
    refs = TaskRefRegistry(statuses, [PriorityRef(id=1, code="low")])
    ordered = refs.ordered_status_codes()
    validate_status_transition("review", "in_progress", ordered_codes=ordered)
    with pytest.raises(InvalidStatusTransitionError, match="Нельзя пропускать статусы"):
        validate_status_transition("todo", "done", ordered_codes=ordered)


def test_terminal_is_last_sort_order() -> None:
    refs = _default_registry()
    assert refs.terminal_status_code() == "done"
