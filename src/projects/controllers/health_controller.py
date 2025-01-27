from pydantic import BaseModel
from projects.controllers.base import BaseController, controller


class HealthCheckResponse(BaseModel):
    status: str


@controller
class HealthCheckController(BaseController):
    def __init__(self) -> None:
        super().__init__(prefix="/health")

    def init_routes(self) -> None:
        self.router.get("")(self.health_check)

    def health_check(self) -> HealthCheckResponse:
        return HealthCheckResponse(status="OK")
