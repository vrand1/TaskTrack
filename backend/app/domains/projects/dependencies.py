from typing import Annotated

from fastapi import Depends

from app.api.dependencies import SessionDep
from app.domains.projects.repository import ProjectRepository
from app.domains.projects.service import ProjectService


def get_project_service(session: SessionDep) -> ProjectService:
    return ProjectService(ProjectRepository(session))


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
