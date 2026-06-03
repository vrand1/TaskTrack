from typing import Any

from app.domains.tasks.domain.refs import TaskRefRegistry
from app.domains.tasks.models import Task
from app.domains.tasks.repositories.task import TaskRepository
from app.domains.tasks.services.parent_rules import ParentTaskRules
from app.domains.users.ports import UserStore


async def apply_task_update(
    task: Task,
    updates: dict[str, Any],
    *,
    repository: TaskRepository,
    users: UserStore,
    refs: TaskRefRegistry,
    parent_rules: ParentTaskRules,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []

    if "parent_task_id" in updates:
        new_parent_id = updates.pop("parent_task_id")
        await parent_rules.validate_parent(
            project_id=task.project_id,
            parent_task_id=new_parent_id,
            task_id=task.id,
        )
        if task.parent_task_id != new_parent_id:
            changes.append(
                {
                    "field": "parent_task_id",
                    "old": str(task.parent_task_id) if task.parent_task_id else None,
                    "new": str(new_parent_id) if new_parent_id else None,
                }
            )
            task.parent_task_id = new_parent_id

    if "assignee" in updates:
        assignee = await users.require_active_by_email(updates.pop("assignee"))
        if task.assignee_id != assignee.id:
            changes.append(
                {
                    "field": "assignee",
                    "old": task.assignee_user.email,
                    "new": assignee.email,
                }
            )
            task.assignee_id = assignee.id

    if "priority" in updates:
        priority_code = updates.pop("priority")
        new_priority_id = refs.priority_id(priority_code)
        if task.priority_id != new_priority_id:
            changes.append(
                {
                    "field": "priority",
                    "old": refs.priority_code(task.priority_id),
                    "new": priority_code,
                }
            )
            task.priority_id = new_priority_id

    if "tags" in updates:
        new_tags = updates.pop("tags")
        old_tags = sorted(row.tag.name for row in task.tags)
        if old_tags != new_tags:
            changes.append({"field": "tags", "old": old_tags, "new": new_tags})
            await repository.set_tags(task, new_tags)

    for field, value in updates.items():
        old_value = getattr(task, field)
        if old_value != value:
            changes.append({"field": field, "old": old_value, "new": value})
        setattr(task, field, value)

    return changes
