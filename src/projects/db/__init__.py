from injector import Module, provider
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from projects.config import ProjectServiceConfigurations

from ..core.services.projects import ProjectRepository
from ..db.project_repository import ProjectRepositoryOnSQLA


class DatabaseModule(Module):
    @provider
    def provide_session(self, config: ProjectServiceConfigurations) -> AsyncSession:
        engine = create_async_engine(config.DB_URI)
        return async_sessionmaker(engine, class_=AsyncSession)()

    @provider
    def provide_project_repository(self, session: AsyncSession) -> ProjectRepository:
        return ProjectRepositoryOnSQLA(session=session)
