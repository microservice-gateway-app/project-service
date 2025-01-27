from collections.abc import Sequence
from datetime import date
from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from ..domain.project import Project, ProjectId
from ..domain.user import User, UserId


class ProjectFilters(BaseModel):
    name_contains: str | None = None
    description_contains: str | None = None
    start_date_from: date | None = None
    start_date_to: date | None = None
    end_date_from: date | None = None
    end_date_to: date | None = None
    created_by: UserId | None = None
    archived: bool | None = None

    @field_validator("created_by", mode="before")
    @classmethod
    def validate_created_by(cls, value: Any) -> UserId:
        if isinstance(value, UserId):
            return value
        if isinstance(value, str):
            return UserId(value=value)
        raise ValueError(f"Invalid UserId value: {value}")


class Pagination(BaseModel):
    page: int = Field(description="Page number starting from 1", gt=0)
    page_size: int = Field(description="Number of items in a page", gt=0)


class ProjectSpecs(BaseModel):
    filters: ProjectFilters | None = Field(
        default=None, description="Filters to apply on projects"
    )
    pagination: Pagination | None = Field(
        default=None, description="Pagination parameters"
    )
    sort: str | None = Field(
        default=None, description="Column to sort returned list based on"
    )
    subset: list[str] | None = Field(
        default=None, description="Subset of fields to return"
    )


class ProjectListWithCount(BaseModel):
    projects: Sequence[Project] = Field(default_factory=list)
    count: int = Field()


class ProjectCreate(BaseModel):
    name: str
    description: str
    start_date: date
    end_date: date
    created_by: SkipJsonSchema[User | None] = Field(default=None, exclude=True)


class ProjectEdit(BaseModel):
    name: Optional[str] = Field(default=None, description="The name of the project")
    description: Optional[str] = Field(
        default=None, description="The description of the project"
    )
    start_date: Optional[date] = Field(
        default=None, description="The start date of the project"
    )
    end_date: Optional[date] = Field(
        default=None, description="The end date of the project"
    )


class ProjectRepository(Protocol):
    async def find(self, *, specs: ProjectSpecs) -> ProjectListWithCount: ...

    async def find_by_id(self, *, id: ProjectId) -> Optional[Project]: ...

    async def save(self, *, project: Project) -> None: ...

    async def archive(self, *, id: ProjectId) -> None: ...

    async def delete(self, *, id: ProjectId) -> None: ...


class ProjectServices:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    async def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(
            name=payload.name,
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            created_by=payload.created_by,
        )
        await self.repository.save(project=project)
        return project

    async def query_projects(
        self,
        specs: ProjectSpecs,
        owner_id: UserId | None = None,
    ) -> ProjectListWithCount:
        if owner_id:
            filters = specs.filters.model_copy() if specs.filters else ProjectFilters()
            filters.created_by = owner_id
            specs.filters = filters
        return await self.repository.find(specs=specs)

    async def get_project_by_id(
        self,
        id: ProjectId,
        owner_id: UserId | None = None,
    ) -> Optional[Project]:
        maybe_project = await self.repository.find_by_id(id=id)
        if not (project := maybe_project) or (
            owner_id and project.created_by.id != owner_id
        ):
            return None
        return project

    async def edit_project(
        self,
        id: ProjectId,
        edit: ProjectEdit,
        owner_id: UserId | None = None,
    ) -> Optional[Project]:
        project = await self.get_project_by_id(id=id, owner_id=owner_id)
        if not project:
            return None

        updated_fields = edit.model_dump(exclude_unset=True)
        for key, value in updated_fields.items():
            if value is not None:
                setattr(project, key, value)

        await self.repository.save(project=project)
        return project

    async def archive_project(
        self,
        id: ProjectId,
        owner_id: UserId | None = None,
    ) -> bool:
        project = await self.get_project_by_id(id=id, owner_id=owner_id)
        if not project:
            return False
        await self.repository.archive(id=id)
        return True

    async def delete_project(
        self,
        id: ProjectId,
        owner_id: UserId | None = None,
    ) -> bool:
        project = await self.get_project_by_id(id=id, owner_id=owner_id)
        if not project:
            return False
        await self.repository.delete(id=id)
        return True
