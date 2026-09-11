import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from library.domain.audit.actor import AuditActor
from library.domain.entities import Entity
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject
from library.domain.value_objects.users import OrganizationID

COMMAND_TTL_EXPIRY_DAYS = 1


class CommandPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    SERVICE: ClassVar[Service]


class CommandID(IDValueObject):
    pass


class Command[CommandPayloadT: CommandPayload](Entity[CommandID]):
    model_config = ConfigDict(frozen=True)

    id: CommandID = Field(default_factory=lambda: CommandID())
    organization_id: OrganizationID
    payload: CommandPayloadT
    actor: AuditActor | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dispatched_at: datetime | None = None
    processed_at: datetime | None = None
    delay_seconds: int = 0
    ttl: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(days=COMMAND_TTL_EXPIRY_DAYS))
    success: bool | None = None
    attempt_count: int = 0
    service: Service = Field(default_factory=lambda: Service(os.environ["SERVICE"]))

    @computed_field
    @property
    def name(self) -> str:
        return self.payload.__class__.__name__

    @computed_field
    @property
    def executor_name(self) -> str:
        without_suffix = self.name.removesuffix("Command")
        without_suffix_snake_case = re.sub("(?<!^)(?=[A-Z])", "_", without_suffix).lower()
        return without_suffix_snake_case


class CommandRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: CommandID
    organization_id: OrganizationID
    created_at: datetime
    dispatched_at: datetime | None
    processed_at: datetime | None
    delay_seconds: int
    payload: dict[str, Any]
    actor: AuditActor | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    name: str
    executor_name: str
    ttl: datetime
    success: bool | None
    attempt_count: int = 0
    service: str

    @classmethod
    def get_subentity_names(cls) -> list[str]:
        return []
