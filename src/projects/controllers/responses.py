from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseWithData(BaseModel, Generic[T]):
    data: T
