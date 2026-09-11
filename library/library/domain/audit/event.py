from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from library.domain.audit.action import AuditAction
from library.domain.audit.actor import AuditActor
from library.domain.audit.change import FieldChange
from library.domain.entities import Entity
from library.domain.value_objects.core import EnumValueObject, IDValueObject
from library.domain.value_objects.users import OrganizationID

AUDIT_TTL_EXPIRY_DAYS = 1
AUDIT_SCHEMA_VERSION = 1


class AuditSource(EnumValueObject):
    REST = "rest"
    EXECUTOR = "executor"
    LISTENER = "listener"
    JOB = "job"
    MCP = "mcp"
    WEBHOOK = "webhook"
    SYSTEM = "system"


class AuditEventPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int
    occurred_at: datetime
    action: AuditAction
    actor: AuditActor
    organization_id: OrganizationID | None
    environment: str
    service: str
    resource_type: str
    resource_id: str
    changes: list[FieldChange] | None
    source: AuditSource
    correlation_id: str | None
    causation_id: str | None
    trace_id: str | None
    request_id: str | None
    ip_address: str | None
    user_agent: str | None

    @classmethod
    def pubsub_event_name(cls) -> str:
        return cls.__name__


class AuditEventID(IDValueObject):
    pass


class AuditEvent(Entity[AuditEventID]):
    model_config = ConfigDict(frozen=True)

    id: AuditEventID = Field(default_factory=lambda: AuditEventID())
    organization_id: OrganizationID | None
    published_at: datetime | None = None
    payload: AuditEventPayload
    ttl: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(days=AUDIT_TTL_EXPIRY_DAYS))

    @computed_field
    @property
    def name(self) -> str:
        return self.payload.action


class AuditEventRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: AuditEventID
    organization_id: OrganizationID | None
    published_at: datetime | None
    payload: dict[str, Any]
    name: str

    @classmethod
    def get_subentity_names(cls) -> list[str]:
        return []
