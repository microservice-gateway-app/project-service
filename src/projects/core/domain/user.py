from pydantic import BaseModel

from .uuid import UUID


class UserId(UUID, frozen=True): ...


class User(BaseModel):
    id: UserId
