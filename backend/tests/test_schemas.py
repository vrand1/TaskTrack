import pytest
from pydantic import ValidationError

from app.domains.tasks.schemas import TaskCreate, TaskStatusUpdate, TaskUpdate
from tests.users import AdminUser


def test_create_strips_whitespace() -> None:
    import uuid

    task = TaskCreate(
        project_id=uuid.uuid4(),
        title="  Fix bug  ",
        assignee=f"  {AdminUser.email}  ",
    )
    assert task.title == "Fix bug"
    assert task.assignee == AdminUser.email


def test_create_rejects_empty_title() -> None:
    import uuid

    with pytest.raises(ValidationError):
        TaskCreate(project_id=uuid.uuid4(), title="   ", assignee=AdminUser.email)


def test_create_rejects_invalid_priority() -> None:
    import uuid

    with pytest.raises(ValidationError, match="Некорректный приоритет"):
        TaskCreate(
            project_id=uuid.uuid4(),
            title="Task",
            assignee=AdminUser.email,
            priority="urgent",  # type: ignore[arg-type]
        )


def test_status_update_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError, match="Некорректный статус"):
        TaskStatusUpdate(status="archived")  # type: ignore[arg-type]


def test_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="хотя бы одно поле"):
        TaskUpdate()


def test_update_empty_description_becomes_none() -> None:
    task = TaskUpdate(description="")
    assert task.description is None
