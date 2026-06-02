
from sqlalchemy import text

ACTIVE_ROW = text("deleted_at IS NULL")
PURGE_ROW = text("deleted_at IS NOT NULL")
