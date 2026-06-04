import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.indexes import ACTIVE_ROW, PURGE_ROW

if TYPE_CHECKING:
    from app.domains.projects.model import Project
    from app.domains.tasks.models.comment import TaskComment
    from app.domains.tasks.models.event import TaskEvent
    from app.domains.tasks.models.priority import TaskPriorityRef
    from app.domains.tasks.models.status import TaskStatusRef
    from app.domains.tasks.models.tag import TaskTag
    from app.domains.users.model import User


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index(
            "ix_tasks_active_project_id",
            "project_id",
            postgresql_where=ACTIVE_ROW,
            sqlite_where=ACTIVE_ROW,
        ),
        Index(
            "ix_tasks_active_assignee_id",
            "assignee_id",
            postgresql_where=ACTIVE_ROW,
            sqlite_where=ACTIVE_ROW,
        ),
        Index(
            "ix_tasks_active_status_id",
            "status_id",
            postgresql_where=ACTIVE_ROW,
            sqlite_where=ACTIVE_ROW,
        ),
        Index(
            "ix_tasks_active_parent_task_id",
            "parent_task_id",
            postgresql_where=ACTIVE_ROW,
            sqlite_where=ACTIVE_ROW,
        ),
        Index(
            "ix_tasks_active_project_created_at",
            "project_id",
            "created_at",
            postgresql_where=ACTIVE_ROW,
            sqlite_where=ACTIVE_ROW,
        ),
        Index(
            "ix_tasks_active_assignee_created_at",
            "assignee_id",
            "created_at",
            postgresql_where=ACTIVE_ROW,
            sqlite_where=ACTIVE_ROW,
        ),
        Index(
            "ix_tasks_purge_deleted_at",
            "deleted_at",
            postgresql_where=PURGE_ROW,
            sqlite_where=PURGE_ROW,
        ),
    )
    # UUID не особо оправдан, я просто хотел с ним поработать. Опыта не было, а очень хотелось
    # Как для микросервиса решение окей, глобальная уникальность во всей ИС, но оверинжиниринг бтв
    # в рамках этого задания мини прод сервиса
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4) # type: ignore[assignment]
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id"),
        nullable=True,
        index=True,
    )

    status_id: Mapped[int] = mapped_column(
        ForeignKey("task_statuses.id"), nullable=False, index=True
    )
    priority_id: Mapped[int] = mapped_column(
        ForeignKey("task_priorities.id"), nullable=False, index=True
    )
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    was_reopened: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignee_user: Mapped["User"] = relationship(back_populates="assigned_tasks")
    project: Mapped["Project"] = relationship(back_populates="tasks")
    parent_task: Mapped["Task | None"] = relationship(
        remote_side="Task.id",
        back_populates="subtasks",
    )
    subtasks: Mapped[list["Task"]] = relationship(back_populates="parent_task")
    status_ref: Mapped["TaskStatusRef"] = relationship()
    priority_ref: Mapped["TaskPriorityRef"] = relationship()
    events: Mapped[list["TaskEvent"]] = relationship(
        back_populates="task",
        order_by="TaskEvent.created_at",
    )
    tags: Mapped[list["TaskTag"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["TaskComment"]] = relationship(
        back_populates="task",
        order_by="TaskComment.created_at",
    )
