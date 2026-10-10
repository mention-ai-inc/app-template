from typing import Literal

from pydantic import BaseModel

HEALTH_PATH = "/health"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def health_handler() -> HealthResponse:
    return HealthResponse()
