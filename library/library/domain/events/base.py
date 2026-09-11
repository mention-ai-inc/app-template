from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from library.domain.audit.actor import AuditActor
from library.domain.entities import Entity
from library.domain.value_objects.core import IDValueObject
from library.domain.value_objects.users import OrganizationID

EVENT_TTL_EXPIRY_DAYS = 1


class EventPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    @classmethod
    def pubsub_event_name(cls) -> str:
        return cls.__name__


class EventID(IDValueObject):
    pass


class Event[EventPayloadT: EventPayload](Entity[EventID]):
    model_config = ConfigDict(frozen=True)

    id: EventID = Field(default_factory=lambda: EventID())
    organization_id: OrganizationID | None
    published_at: datetime | None = None
    payload: EventPayloadT
    actor: AuditActor | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    ttl: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(days=EVENT_TTL_EXPIRY_DAYS))

    @computed_field
    @property
    def name(self) -> str:
        return self.payload.__class__.__name__


class EventRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: EventID
    organization_id: OrganizationID | None
    published_at: datetime | None
    payload: dict[str, Any]
    actor: AuditActor | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    name: str

    @classmethod
    def get_subentity_names(cls) -> list[str]:
        return []
