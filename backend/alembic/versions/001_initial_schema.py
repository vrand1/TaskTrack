from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEV_PASSWORD_HASH = "$2b$12$RhqPftDg4TKir8Nq0DN06e0rteyXEGEYOFnKQQc6JPhiTLg7XCGAe"
# На проде я бы такое не сделал, мне бы за такое руки девопс оторвал :(
_ACTIVE = sa.text("deleted_at IS NULL")
_PURGE = sa.text("deleted_at IS NOT NULL")

TASK_STATUSES = [
    {"id": 1, "code": "todo", "sort_order": 1},
    {"id": 2, "code": "in_progress", "sort_order": 2},
    {"id": 3, "code": "review", "sort_order": 3},
    {"id": 4, "code": "done", "sort_order": 4},
]

TASK_PRIORITIES = [
    {"id": 1, "code": "low"},
    {"id": 2, "code": "medium"},
    {"id": 3, "code": "high"},
]

USERS = [
    {
        "id": 1,
        "email": "admin@example.dev",
        "password_hash": DEV_PASSWORD_HASH,
        "is_active": True,
        "is_admin": True,
    },
    {
        "id": 2,
        "email": "user@example.dev",
        "password_hash": DEV_PASSWORD_HASH,
        "is_active": True,
        "is_admin": False,
    },
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.bulk_insert(
        sa.table(
            "users",
            sa.column("id", sa.Integer()),
            sa.column("email", sa.String()),
            sa.column("password_hash", sa.String()),
            sa.column("is_active", sa.Boolean()),
            sa.column("is_admin", sa.Boolean()),
        ),
        USERS,
    )

    op.create_table(
        "task_statuses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "task_priorities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.bulk_insert(
        sa.table(
            "task_statuses",
            sa.column("id", sa.Integer()),
            sa.column("code", sa.String()),
            sa.column("sort_order", sa.Integer()),
        ),
        TASK_STATUSES,
    )
    op.bulk_insert(
        sa.table(
            "task_priorities",
            sa.column("id", sa.Integer()),
            sa.column("code", sa.String()),
        ),
        TASK_PRIORITIES,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("SELECT setval(pg_get_serial_sequence('users', 'id'), 2)"))
        op.execute(sa.text("SELECT setval(pg_get_serial_sequence('task_statuses', 'id'), 4)"))
        op.execute(sa.text("SELECT setval(pg_get_serial_sequence('task_priorities', 'id'), 3)"))

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_index(
        "ix_projects_active_created_at",
        "projects",
        ["created_at"],
        unique=False,
        postgresql_where=_ACTIVE,
        sqlite_where=_ACTIVE,
    )
    op.create_index(
        "ix_projects_purge_deleted_at",
        "projects",
        ["deleted_at"],
        unique=False,
        postgresql_where=_PURGE,
        sqlite_where=_PURGE,
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assignee_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("parent_task_id", sa.Uuid(), nullable=True),
        sa.Column("status_id", sa.Integer(), nullable=False),
        sa.Column("priority_id", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("was_reopened", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["parent_task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["priority_id"], ["task_priorities.id"]),
        sa.ForeignKeyConstraint(["status_id"], ["task_statuses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"], unique=False)
    op.create_index("ix_tasks_status_id", "tasks", ["status_id"], unique=False)
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"], unique=False)
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"], unique=False)
    op.create_index("ix_tasks_priority_id", "tasks", ["priority_id"], unique=False)
    op.create_index("ix_tasks_active_start_at", "tasks", ["start_at"], unique=False)
    op.create_index("ix_tasks_active_end_at", "tasks", ["end_at"], unique=False)
    op.create_index(
        "ix_tasks_purge_deleted_at",
        "tasks",
        ["deleted_at"],
        unique=False,
        postgresql_where=_PURGE,
        sqlite_where=_PURGE,
    )
    for name, column in (
        ("ix_tasks_active_project_id", "project_id"),
        ("ix_tasks_active_assignee_id", "assignee_id"),
        ("ix_tasks_active_status_id", "status_id"),
        ("ix_tasks_active_parent_task_id", "parent_task_id"),
    ):
        op.create_index(
            name,
            "tasks",
            [column],
            unique=False,
            postgresql_where=_ACTIVE,
            sqlite_where=_ACTIVE,
        )
    op.create_index(
        "ix_tasks_active_project_created_at",
        "tasks",
        ["project_id", "created_at"],
        unique=False,
        postgresql_where=_ACTIVE,
        sqlite_where=_ACTIVE,
    )
    op.create_index(
        "ix_tasks_active_assignee_created_at",
        "tasks",
        ["assignee_id", "created_at"],
        unique=False,
        postgresql_where=_ACTIVE,
        sqlite_where=_ACTIVE,
    )

    json_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")

    op.create_table(
        "task_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_events_task_id_created_at",
        "task_events",
        ["task_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_task_events_task_id_event_type",
        "task_events",
        ["task_id", "event_type"],
        unique=False,
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )
    op.create_index("ix_task_tags_tag_id", "task_tags", ["tag_id"])

    op.create_table(
        "task_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_comments_task_id_created_at",
        "task_comments",
        ["task_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_idempotency_keys_scope", "idempotency_keys", ["scope"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_scope", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index("ix_task_comments_task_id_created_at", table_name="task_comments")
    op.drop_table("task_comments")
    op.drop_index("ix_task_tags_tag_id", table_name="task_tags")
    op.drop_table("task_tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_task_events_task_id_event_type", table_name="task_events")
    op.drop_index("ix_task_events_task_id_created_at", table_name="task_events")
    op.drop_table("task_events")
    op.drop_index("ix_tasks_active_assignee_created_at", table_name="tasks")
    op.drop_index("ix_tasks_active_project_created_at", table_name="tasks")
    op.drop_index("ix_tasks_active_parent_task_id", table_name="tasks")
    op.drop_index("ix_tasks_active_status_id", table_name="tasks")
    op.drop_index("ix_tasks_active_assignee_id", table_name="tasks")
    op.drop_index("ix_tasks_active_project_id", table_name="tasks")
    op.drop_index("ix_tasks_purge_deleted_at", table_name="tasks")
    op.drop_index("ix_tasks_active_end_at", table_name="tasks")
    op.drop_index("ix_tasks_active_start_at", table_name="tasks")
    op.drop_index("ix_tasks_priority_id", table_name="tasks")
    op.drop_index("ix_tasks_parent_task_id", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_index("ix_tasks_status_id", table_name="tasks")
    op.drop_index("ix_tasks_assignee_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_projects_purge_deleted_at", table_name="projects")
    op.drop_index("ix_projects_active_created_at", table_name="projects")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")
    op.drop_table("task_priorities")
    op.drop_table("task_statuses")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
