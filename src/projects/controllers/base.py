import abc
import re
from typing import TypeVar

from fastapi import APIRouter


def camel_to_words(name: str) -> str:
    # Replace capital letters with ` ` + lowercase letter
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower().split()
    return " ".join(w.capitalize() for w in words)


class BaseController(abc.ABC):
    def __init__(self, *, prefix: str | None = None) -> None:
        controller_name = camel_to_words(
            self.__class__.__name__.removesuffix("Controller")
        )
        self.router = APIRouter(
            prefix=prefix or "",
            tags=[controller_name],
        )
        self.init_routes()

    @abc.abstractmethod
    def init_routes(self) -> None: ...


T = TypeVar("T", bound=BaseController)

class Controllers:
    controllers = list[type[BaseController]]()

    @classmethod
    def register(cls, controller: type[BaseController]) -> None:
        cls.controllers.append(controller)


def controller(cls: type[T]):
    """Register a controller to a centralized registry"""
    Controllers.register(cls)
    return cls
