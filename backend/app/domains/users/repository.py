
from app.domains.users.adapters.sqlalchemy import SqlAlchemyUserStore

UserRepository = SqlAlchemyUserStore

__all__ = ["UserRepository", "SqlAlchemyUserStore"]
