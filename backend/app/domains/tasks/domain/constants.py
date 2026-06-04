DEFAULT_TASK_STATUS = "todo"
DEFAULT_TASK_PRIORITY = "medium"

# Справочник статусов/приоритетов в БД (task_statuses, task_priorities):
# задел под настраиваемый workflow.
# FSM и FK читают коды из TaskRefRegistry при старте. Ниже — фиксированный набор.
# Чтобы добавить статус только через БД, нужно ещё обновить эти консты и перезапустить API

# TODO вынести в динамику TASK_STATUSES и TASK_PRIORITIES с подкл к редис
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
