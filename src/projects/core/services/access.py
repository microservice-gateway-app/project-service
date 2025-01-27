from collections.abc import Collection
from enum import Enum

from pydantic import BaseModel, Field

from ..domain.user import User, UserId


class ProjectScope(Enum):
    PROJECT_READ = "projects"
    PROJECT_WRITE = "projects.write"
    PROJECT_READ_SELF = "projects:self"
    PROJECT_WRITE_SELF = "projects:self.write"


class Actor(BaseModel):
    user_id: UserId = Field()
    scopes: list[ProjectScope] = Field(default_factory=list)

    def has_scope(self, scope: ProjectScope) -> bool:
        return any(s == scope for s in self.scopes)

    def has_any_scope(self, scopes: Collection[ProjectScope]) -> bool:
        return any(set(self.scopes).intersection(scopes))

    def to_user(self) -> User:
        return User(id=self.user_id)
