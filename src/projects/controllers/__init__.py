from fastapi import FastAPI
from injector import Binder, Injector, Module, provider

from projects.config import ProjectServiceConfigurations
from projects.controllers.access_controller import AccessController
from projects.core.services.projects import ProjectRepository, ProjectServices

from .base import Controllers
from .health_controller import HealthCheckController
from .project_controller import ProjectController


class ControllerModule(Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(HealthCheckController)

    @provider
    def provide_project_controller(
        self, repository: ProjectRepository
    ) -> ProjectController:
        return ProjectController(service=ProjectServices(repository))

    @provider
    def provide_access_controller(
        self, config: ProjectServiceConfigurations
    ) -> AccessController:
        return AccessController(config=config)


def register_controllers_to_app(app: FastAPI, injector: Injector) -> FastAPI:
    for controller in Controllers.controllers:
        print(f"Discovered controller {controller}")
        app.include_router(injector.get(controller).router)
    return app
