from __future__ import annotations

import traceback
from typing import Annotated

from fastapi import Body, HTTPException, Security
from pydantic import Field, ValidationError

from ..core.domain.project import Project, ProjectId, Revision
from ..core.domain.user import UserId
from ..core.services.access import Actor, ProjectScope
from ..core.services.projects import (
    ProjectCreate,
    ProjectEdit,
    ProjectServices,
    ProjectSpecs,
)
from ..middlewares.access_scopes import has_any_scope
from .base import BaseController, controller
from .responses import ResponseWithData


class ProjectResponse(ResponseWithData[Project]):
    pass


class ProjectWithoutRevisionHistory(Project):
    revisions: list[Revision] = Field(default_factory=list, exclude=True)

    @staticmethod
    def from_project(project: Project) -> ProjectWithoutRevisionHistory:
        obj = ProjectWithoutRevisionHistory(**project.model_dump(exclude={"team"}))
        obj.team = project.team
        return obj


class ProjectListResponse(ResponseWithData[list[ProjectWithoutRevisionHistory]]):
    total_count: int = Field(..., description="Total number of projects")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of projects per page")


def get_read_owner(actor: Actor) -> UserId | None:
    return actor.user_id if actor.has_scope(ProjectScope.PROJECT_READ) else None


def get_write_owner(actor: Actor) -> UserId | None:
    return actor.user_id if actor.has_scope(ProjectScope.PROJECT_WRITE) else None


@controller
class ProjectController(BaseController):
    def __init__(self, service: ProjectServices):
        super().__init__(prefix="/projects")
        self.service = service

    def init_routes(self) -> None:
        router = self.router

        router.post(
            "/query",
            response_model=ProjectListResponse,
        )(self.query_projects)

        router.get(
            "/{id:str}",
            response_model=ProjectResponse,
        )(self.get_project_by_id)

        router.post("")(self.create_project)
        router.patch("/{id:str}")(self.edit_project)
        router.patch("/{id:str}/archive")(self.archive_project)
        router.delete("/{id:str}")(self.delete_project)

    async def query_projects(
        self,
        specs: Annotated[ProjectSpecs, Body()],
        actor: Actor = Security(
            has_any_scope,
            scopes=[
                ProjectScope.PROJECT_READ.value,
                ProjectScope.PROJECT_READ_SELF.value,
            ],
        ),
    ) -> ProjectListResponse:
        """Required scopes: projects or projects:self"""
        result = await self.service.query_projects(
            specs, owner_id=get_read_owner(actor)
        )
        projects = result.projects
        count = result.count
        project_list = [
            ProjectWithoutRevisionHistory.from_project(proj) for proj in projects
        ]
        page = specs.pagination.page if specs.pagination else 1
        page_size = specs.pagination.page_size if specs.pagination else len(projects)
        return ProjectListResponse(
            data=project_list, total_count=count, page=page, page_size=page_size
        )

    async def create_project(
        self,
        payload: Annotated[ProjectCreate, Body()],
        actor: Actor = Security(
            has_any_scope,
            scopes=[
                ProjectScope.PROJECT_WRITE.value,
                ProjectScope.PROJECT_WRITE_SELF.value,
            ],
        ),
    ) -> ProjectResponse:
        """Required scopes: projects:write or projects:self.write"""
        payload.created_by = actor.to_user()
        project = await self.service.create_project(payload)
        return ProjectResponse(data=project)

    async def get_project_by_id(
        self,
        id: str,
        actor: Actor = Security(
            has_any_scope,
            scopes=[
                ProjectScope.PROJECT_READ.value,
                ProjectScope.PROJECT_READ_SELF.value,
            ],
        ),
    ) -> ProjectResponse:
        """Required scopes: projects or projects:self"""
        try:
            project = await self.service.get_project_by_id(
                id=ProjectId(value=id), owner_id=get_read_owner(actor)
            )
        except ValidationError as exc:
            traceback.print_exception(exc)
            project = None
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectResponse(data=project)

    async def edit_project(
        self,
        id: str,
        edit: ProjectEdit,
        actor: Actor = Security(
            has_any_scope,
            scopes=[
                ProjectScope.PROJECT_WRITE.value,
                ProjectScope.PROJECT_WRITE_SELF.value,
            ],
        ),
    ) -> ProjectResponse:
        """Required scopes: projects:write or projects:self.write"""
        project = await self.service.edit_project(
            id=ProjectId(value=id), edit=edit, owner_id=get_write_owner(actor)
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectResponse(data=project)

    async def archive_project(
        self,
        id: str,
        actor: Actor = Security(
            has_any_scope,
            scopes=[
                ProjectScope.PROJECT_WRITE.value,
                ProjectScope.PROJECT_WRITE_SELF.value,
            ],
        ),
    ) -> None:
        """Required scopes: projects:write or projects:self.write"""
        success = await self.service.archive_project(
            id=ProjectId(value=id), owner_id=get_write_owner(actor)
        )
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")

    async def delete_project(
        self,
        id: str,
        actor: Actor = Security(
            has_any_scope,
            scopes=[
                ProjectScope.PROJECT_WRITE.value,
                ProjectScope.PROJECT_WRITE_SELF.value,
            ],
        ),
    ) -> None:
        """Required scopes: projects:write or projects:self.write"""
        success = await self.service.delete_project(
            id=ProjectId(value=id), owner_id=get_write_owner(actor)
        )
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
