from __future__ import annotations

from datetime import datetime

from google.protobuf.timestamp_pb2 import Timestamp

from app.domains.projects.schemas import ProjectRead
from app.domains.tasks.schemas import TaskRead

from .generated import task_service_pb2 as pb2


def to_timestamp(value: datetime | None) -> Timestamp:
    if value is None:
        return Timestamp()
    ts = Timestamp()
    ts.FromDatetime(value)
    return ts


def to_proto_project(project: ProjectRead) -> pb2.Project:
    return pb2.Project(
        id=str(project.id),
        slug=project.slug,
        name=project.name,
        description=project.description or "",
        created_by=project.created_by,
        created_at=to_timestamp(project.created_at),
        updated_at=to_timestamp(project.updated_at),
    )


def to_proto_task(task: TaskRead) -> pb2.Task:
    return pb2.Task(
        id=str(task.id),
        project_id=str(task.project_id),
        parent_task_id=str(task.parent_task_id) if task.parent_task_id else "",
        title=task.title,
        description=task.description or "",
        assignee=task.assignee,
        status=task.status,
        priority=task.priority,
        start_at=to_timestamp(task.start_at),
        end_at=to_timestamp(task.end_at),
        tags=task.tags,
        created_at=to_timestamp(task.created_at),
        updated_at=to_timestamp(task.updated_at),
    )
