from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Справочник статусов в БД; переходы задаются sort_order и TaskRefRegistry + FSM.
class TaskStatusRef(Base):
    __tablename__ = "task_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
