from typing import Self

from pydantic import BaseModel, ConfigDict

from library.domain.value_objects.common import Service
from library.domain.value_objects.core import EnumValueObject


class AuditActorType(EnumValueObject):
    USER = "user"
    SERVICE = "service"
    SYSTEM = "system"
    INTEGRATION = "integration"
    ANONYMOUS = "anonymous"
    OPERATOR = "operator"


class AuditActor(BaseModel):
    model_config = ConfigDict(frozen=True)

    actor_type: AuditActorType
    actor_id: str | None
    actor_email: str | None
    actor_role: str | None
    impersonated_by: Service | None

    @classmethod
    def system(cls) -> Self:
        return cls(
            actor_type=AuditActorType.SYSTEM,
            actor_id=None,
            actor_email=None,
            actor_role=None,
            impersonated_by=None,
        )

    @classmethod
    def service(cls, service: Service, /) -> Self:
        return cls(
            actor_type=AuditActorType.SERVICE,
            actor_id=service,
            actor_email=None,
            actor_role=None,
            impersonated_by=None,
        )
