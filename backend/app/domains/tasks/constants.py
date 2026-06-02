DEFAULT_TASK_STATUS = "todo"
DEFAULT_TASK_PRIORITY = "medium"

TASK_STATUSES = ("todo", "in_progress", "review", "done")
TASK_PRIORITIES = ("low", "medium", "high")

EVENT_CREATED = "created"
EVENT_UPDATED = "updated"
EVENT_STATUS_CHANGED = "status_changed"
EVENT_DELETED = "deleted"
EVENT_RESTORED = "restored"
EVENT_COMMENT_ADDED = "comment_added"

TASK_EVENT_TYPES = (
    EVENT_CREATED,
    EVENT_UPDATED,
    EVENT_STATUS_CHANGED,
    EVENT_DELETED,
    EVENT_RESTORED,
    EVENT_COMMENT_ADDED,
)
