from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .role import Role
from .user import User, UserId
from .uuid import UUID


def timestamp_now():
    return datetime.now(UTC)


class ProjectId(UUID, frozen=True): ...


class Team(BaseModel):
    members: list[User] = Field(default_factory=list)
    roles: dict[UserId, Role] = Field(default_factory=dict)

    def add_member(self, user: User, role: Role) -> None:
        self.members.append(user)
        self.roles[user.id] = role

    def remove_member(self, user_id: UserId) -> None:
        self.members = [m for m in self.members if m.id != user_id]
        self.roles.pop(user_id, None)

    def update_member_role(self, user_id: UserId, role: Role | None) -> None:
        if user_id not in self.roles:
            raise ValueError(f"User {user_id} is not a member of the team.")
        if role is None:
            self.roles.pop(user_id)
            return
        self.roles[user_id] = role


class PhaseId(UUID, frozen=True): ...


class Phase(BaseModel):
    id: PhaseId = Field(default_factory=PhaseId)
    start_date: date = Field()
    end_date: date = Field()

    def is_active(self) -> bool:
        today = datetime.now().date()
        return self.start_date <= today <= self.end_date


class RevisionId(UUID, frozen=True): ...


class Revision(BaseModel):
    id: RevisionId = Field(frozen=True)
    timestamp: datetime = Field(default_factory=timestamp_now, frozen=True)
    change_content: dict[str, Any] = Field(frozen=True)


class Project(BaseModel):
    id: ProjectId = Field(default_factory=ProjectId, frozen=True)
    name: str = Field()
    description: str = Field()
    start_date: date = Field()
    end_date: date = Field()
    created_by: User = Field(frozen=True)
    created_at: datetime = Field(default_factory=timestamp_now, frozen=True)
    revisions: list[Revision] = Field(default_factory=list)
    phases: list[Phase] = Field(default_factory=list)
    team: Team = Field(default_factory=Team)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        if not kwargs.get("revision"):
            initial_revision = Revision(
                id=RevisionId(),
                change_content={
                    "project_created": {
                        "name": self.name,
                        "description": self.description,
                    }
                },
            )
            self.revisions.append(initial_revision)
        if not kwargs.get("team"):
            self.team.add_member(user=self.created_by, role=Role.OWNER)

    def is_owner(self, user_id: UserId) -> bool:
        return self.created_by.id == user_id

    def is_editor(self, user_id: UserId) -> bool:
        role = self.team.roles.get(user_id)
        return role is not None and role.is_editor()

    def is_viewer(self, user_id: UserId) -> bool:
        role = self.team.roles.get(user_id)
        return role is not None and role.is_viewer()

    def add_member(self, user: User, role: Role) -> None:
        self.team.add_member(user, role)
        self.create_revision(
            change_content={"added_member": {"user_id": user.id, "role": role}}
        )

    def remove_member_role(self, user_id: UserId, role: Role) -> None:
        if self.team.roles.get(user_id) == role:
            self.team.update_member_role(user_id, None)
            self.create_revision(
                change_content={"removed_role": {"role": role, "user_id": user_id}}
            )
        else:
            raise ValueError(f"Role {role} for user {user_id} does not exist.")

    def remove_member(self, user_id: UserId) -> None:
        self.team.remove_member(user_id)
        self.create_revision(change_content={"removed_member": user_id})

    def create_revision(self, change_content: dict[str, Any]) -> None:
        revision = Revision(id=RevisionId(), change_content=change_content)
        self.revisions.append(revision)
