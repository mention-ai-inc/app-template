from typing import Any

from pydantic import BaseModel, ConfigDict


class FieldChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    before: Any | None
    after: Any | None
    value_captured: bool
