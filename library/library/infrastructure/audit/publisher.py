import logging
import os
from datetime import UTC, datetime
from typing import Self

from library.application.audit.context import get_audit_context
from library.domain.audit.action import AuditAction
from library.domain.audit.actor import AuditActor
from library.domain.audit.change import FieldChange
from library.domain.audit.event import (
    AUDIT_SCHEMA_VERSION,
    AuditEvent,
    AuditEventID,
    AuditEventPayload,
    AuditSource,
)
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.persistence.firestore import UOW, Firestore
from library.infrastructure.unit_of_work import get_current_uow
from library.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


class AuditEventPublisher:
    def __init__(
        self,
        *,
        service: str | None = None,
        feature_environment: str | None = None,
    ) -> None:
        self._service = service if service is not None else os.environ["SERVICE"]
        self._feature_environment = feature_environment or os.getenv("FEATURE_ENVIRONMENT", "")
        self._store = Firestore(
            collection="audit",
            model=AuditEvent,
            partition_key_type=OrganizationID,
            service=self._service,
            feature_environment=self._feature_environment,
        )

    @property
    def uow(self) -> UOW:
        return get_current_uow()

    def __call__(self) -> Self:
        return self

    async def save(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        organization_id: OrganizationID | None,
        changes: list[FieldChange] | None,
    ) -> AuditEventID:
        return await self.__write(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            changes=changes,
            uow=self.uow,
        )

    async def quick_save(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        organization_id: OrganizationID | None,
        changes: list[FieldChange] | None,
    ) -> AuditEventID:
        return await self.__write(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            changes=changes,
            uow=None,
        )

    async def __write(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        organization_id: OrganizationID | None,
        changes: list[FieldChange] | None,
        uow: UOW | None,
    ) -> AuditEventID:
        event = AuditEvent(
            organization_id=organization_id,
            payload=self.__build_payload(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                organization_id=organization_id,
                changes=changes,
            ),
        )
        await self._store.set(document_id=self._store.to_document_id(event.id), document_data=event, uow=uow)
        return event.id

    def __build_payload(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        organization_id: OrganizationID | None,
        changes: list[FieldChange] | None,
    ) -> AuditEventPayload:
        context = get_audit_context()
        actor = (context.actor if context is not None else None) or AuditActor.system()
        source = (context.source if context is not None else None) or AuditSource.SYSTEM

        return AuditEventPayload(
            schema_version=AUDIT_SCHEMA_VERSION,
            occurred_at=datetime.now(UTC),
            action=action,
            actor=actor,
            organization_id=organization_id,
            environment=self._feature_environment,
            service=self._service,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            source=source,
            correlation_id=context.correlation_id if context is not None else None,
            causation_id=context.causation_id if context is not None else None,
            trace_id=context.request_id if context is not None else None,
            request_id=context.request_id if context is not None else None,
            ip_address=context.ip_address if context is not None else None,
            user_agent=context.user_agent if context is not None else None,
        )


async def record_audit_best_effort(
    *,
    action: AuditAction,
    resource_type: str,
    resource_id: str,
    organization_id: OrganizationID | None,
    changes: list[FieldChange] | None,
) -> None:
    try:
        await AuditEventPublisher().quick_save(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            changes=changes,
        )
    except Exception as error:
        logger.warning(f"Failed to record audit event ({action}): {error}")
