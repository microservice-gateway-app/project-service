from functools import lru_cache

from fastapi import FastAPI
from injector import Injector, Module, provider, singleton

from .config import provide_config
from .controllers import ControllerModule, register_controllers_to_app
from .db import DatabaseModule


class ProductionModule(Module):
    @singleton
    @provider
    def provide_fastapi_app(self, injector: Injector) -> FastAPI:
        app = FastAPI(title="Project Service", ignore_trailing_slash=True)

        return register_controllers_to_app(app=app, injector=injector)


@lru_cache
def provide_injector() -> Injector:
    injector = Injector(
        modules=[
            provide_config,
            DatabaseModule,
            ControllerModule,
            ProductionModule,
        ]
    )
    injector.get(FastAPI).state.injector = injector
    return injector
