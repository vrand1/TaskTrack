import uuid

from app.core.exceptions import InvalidParentTaskError, TaskNotFoundError
from app.domains.tasks.domain.refs import TaskRefRegistry
from app.domains.tasks.repositories.task import TaskRepository
from app.domains.tasks.schemas import TaskRead


class ParentTaskRules:
    def __init__(self, repository: TaskRepository, refs: TaskRefRegistry) -> None:
        self._repository = repository
        self._refs = refs

    async def validate_parent(
        self,
        *,
        project_id: uuid.UUID,
        parent_task_id: uuid.UUID | None,
        task_id: uuid.UUID | None = None,
    ) -> None:
        if parent_task_id is None:
            return
        if task_id is not None and parent_task_id == task_id:
            raise InvalidParentTaskError("Задача не может быть родителем самой себя")

        try:
            parent = await self._repository.get_active_by_id(parent_task_id)
        except TaskNotFoundError as exc:
            raise InvalidParentTaskError(
                f"Родительская задача {parent_task_id} не найдена"
            ) from exc

        if parent.project_id != project_id:
            raise InvalidParentTaskError("Родительская задача должна принадлежать тому же проекту")

        if task_id is not None:
            await self._ensure_not_descendant(task_id, parent_task_id)

    async def build_subtask_tree(self, parent_id: uuid.UUID) -> list[TaskRead]:
        children = await self._repository.list_children(parent_id)
        result: list[TaskRead] = []
        for child in children:
            nested = await self.build_subtask_tree(child.id)
            result.append(TaskRead.from_db(child, refs=self._refs, subtasks=nested or None))
        return result

    async def _ensure_not_descendant(self, task_id: uuid.UUID, new_parent_id: uuid.UUID) -> None:
        current_id: uuid.UUID | None = new_parent_id
        while current_id is not None:
            if current_id == task_id:
                raise InvalidParentTaskError(
                    "Нельзя назначить родителя: возникнет цикл в дереве задач"
                )
            parent_task = await self._repository.get_active_by_id(current_id)
            current_id = parent_task.parent_task_id
