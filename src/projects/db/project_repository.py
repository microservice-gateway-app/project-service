from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    ColumnElement,
    Date,
    DateTime,
    ForeignKey,
    delete,
    func,
    update,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import and_

from projects.core.domain.user import User, UserId
from projects.db.base import Base

from ..core.domain.project import (
    Phase,
    PhaseId,
    Project,
    ProjectId,
    Revision,
    RevisionId,
)
from ..core.services.projects import (
    ProjectFilters,
    ProjectListWithCount,
    ProjectRepository,
    ProjectSpecs,
)


def to_sqlalchemy_filters(filters: ProjectFilters | None) -> list[ColumnElement[bool]]:
    conditions = list[ColumnElement[bool]]()
    if not filters:
        return conditions

    if filters.name_contains:
        conditions.append(ProjectRecord.name.ilike(filters.name_contains))
    if filters.description_contains:
        conditions.append(ProjectRecord.description.ilike(filters.description_contains))
    if filters.start_date_from:
        conditions.append(ProjectRecord.start_date >= filters.start_date_from)
    if filters.start_date_to:
        conditions.append(ProjectRecord.start_date <= filters.start_date_to)
    if filters.end_date_from:
        conditions.append(ProjectRecord.end_date >= filters.end_date_from)
    if filters.end_date_to:
        conditions.append(ProjectRecord.end_date <= filters.end_date_to)
    if filters.created_by:
        conditions.append(ProjectRecord.created_by == filters.created_by.value)
    if filters.archived is not None:
        conditions.append(ProjectRecord.archived.is_(True))

    return conditions


# SQLAlchemy model
class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    start_date: Mapped[date] = mapped_column(type_=Date)
    end_date: Mapped[date] = mapped_column(type_=Date)
    created_by: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True), server_default=func.current_timestamp()
    )
    archived: Mapped[bool] = mapped_column(default=False)

    phases: Mapped[list[PhaseRecord]] = relationship(
        "PhaseRecord",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectRecord":
        return cls(
            id=project.id.value,
            name=project.name,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            created_by=project.created_by.id.value,
            created_at=project.created_at,
            archived=False,
        )

    def to_domain(self) -> Project:
        return Project(
            id=ProjectId(value=self.id),
            name=self.name,
            description=self.description,
            start_date=self.start_date,
            end_date=self.end_date,
            created_by=User(id=UserId(value=self.created_by)),
            created_at=self.created_at,
            phases=[phase.to_domain() for phase in self.phases],
        )


class PhaseRecord(Base):
    __tablename__ = "phases"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    start_date: Mapped[date] = mapped_column(type_=Date)
    end_date: Mapped[date] = mapped_column(type_=Date)

    project: Mapped[ProjectRecord] = relationship(
        "ProjectRecord", back_populates="phases"
    )

    @classmethod
    def from_domain(cls, phase: Phase, project_id: str) -> "PhaseRecord":
        return cls(
            id=phase.id.value,
            project_id=project_id,
            start_date=phase.start_date,
            end_date=phase.end_date,
        )

    def to_domain(self) -> Phase:
        return Phase(
            id=PhaseId(value=self.id),
            start_date=self.start_date,
            end_date=self.end_date,
        )


class RevisionRecord(Base):
    __tablename__ = "revisions"

    id: Mapped[str] = mapped_column(primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    timestamp: Mapped[datetime] = mapped_column(type_=DateTime(timezone=True))
    change_content: Mapped[dict[str, Any]] = mapped_column(type_=JSON)

    @classmethod
    def from_domain(cls, revision: Revision, project_id: str) -> "RevisionRecord":
        return cls(
            id=revision.id.value,
            project_id=project_id,
            timestamp=revision.timestamp,
            change_content=revision.change_content,
        )

    def to_domain(self) -> Revision:
        return Revision(
            id=RevisionId(value=self.id),
            timestamp=self.timestamp,
            change_content=self.change_content,
        )


class ProjectRepositoryOnSQLA(ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find(self, *, specs: ProjectSpecs) -> ProjectListWithCount:
        """Find projects matching the given specifications."""
        query = select(ProjectRecord).where(and_(*to_sqlalchemy_filters(specs.filters)))
        result = await self.session.execute(query)
        records = result.scalars().all()

        # Assuming specs might include pagination or other filters
        total_count = len(records)
        projects = [record.to_domain() for record in records]

        return ProjectListWithCount(projects=projects, count=total_count)

    async def find_by_id(self, *, id: ProjectId) -> Project | None:
        """Find a project by its ID."""
        try:
            query = select(ProjectRecord).where(ProjectRecord.id == id.value)
            result = await self.session.execute(query)
            record = result.scalar_one()
            return record.to_domain()
        except NoResultFound:
            return None

    async def save(self, *, project: Project) -> None:
        """Save or update a project."""
        record = ProjectRecord.from_domain(project)
        query = select(ProjectRecord).where(ProjectRecord.id == record.id)
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            await self.session.execute(
                update(ProjectRecord)
                .where(ProjectRecord.id == record.id)
                .values(
                    name=record.name,
                    description=record.description,
                    start_date=record.start_date,
                    end_date=record.end_date,
                    archived=record.archived,
                )
            )
        else:
            # Insert new record
            self.session.add(record)

        await self.session.commit()

    async def archive(self, *, id: ProjectId) -> None:
        """Archive a project by setting its archived field to True."""
        await self.session.execute(
            update(ProjectRecord)
            .where(ProjectRecord.id == id.value)
            .values(archived=True)
        )
        await self.session.commit()

    async def delete(self, *, id: ProjectId) -> None:
        """Delete a project by its ID."""
        await self.session.execute(
            delete(ProjectRecord).where(ProjectRecord.id == id.value)
        )
        await self.session.commit()
