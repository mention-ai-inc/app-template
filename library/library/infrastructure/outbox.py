import os
from typing import Any, Self

from library.application.audit.context import get_audit_context
from library.application.ports.documents import IDocumentStore
from library.application.ports.transactions import ITransaction
from library.domain.commands.base import Command, CommandID, CommandPayload
from library.domain.events.base import Event, EventID, EventPayload
from library.domain.outbox import ICommandDispatcher, IEventPublisher
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.unit_of_work import get_current_uow
from library.providers.registry import get_cloud_provider


def _audit_envelope_fields() -> dict[str, Any]:
    context = get_audit_context()
    if context is None:
        return {"actor": None, "correlation_id": None, "causation_id": None}
    return {
        "actor": context.actor,
        "correlation_id": context.correlation_id,
        "causation_id": context.causation_id,
    }


class CommandDispatcher(ICommandDispatcher):
    def __init__(
        self,
        *,
        service: Service | None = None,
        feature_environment: str | None = None,
    ) -> None:
        self._service = service or Service(os.environ["SERVICE"])
        self._feature_environment = feature_environment or os.getenv("FEATURE_ENVIRONMENT", "")
        self._store: IDocumentStore[Command[CommandPayload], CommandID, ITransaction] = (
            get_cloud_provider().document_store(
                collection="commands",
                model=Command[CommandPayload],  # safe to use the base class because we never read from this store
                partition_key_type=CommandID,
                service=self._service,
                feature_environment=self._feature_environment,
            )
        )

    @property
    def uow(self) -> ITransaction:
        return get_current_uow()

    def __call__(self) -> Self:
        return self

    async def save(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None = None,
        delay_seconds: int = 0,
    ) -> CommandID:
        return await self.__write(
            payload, organization_id=organization_id, command_id=command_id, delay_seconds=delay_seconds, uow=self.uow
        )

    async def quick_save(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None = None,
        delay_seconds: int = 0,
    ) -> CommandID:
        # Non-transactional dispatch (direct write, no transaction lease). Use only when the command
        # is the sole write of the operation -- there is no aggregate to keep atomic with it.
        return await self.__write(
            payload, organization_id=organization_id, command_id=command_id, delay_seconds=delay_seconds, uow=None
        )

    async def __write(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None,
        delay_seconds: int,
        uow: ITransaction | None,
    ) -> CommandID:
        command_id = command_id or CommandID()
        await self._store.set(
            document_id=self._store.to_document_id(command_id),
            document_data=Command[Any](
                id=command_id,
                organization_id=organization_id,
                payload=payload,
                delay_seconds=delay_seconds,
                service=payload.SERVICE,
                **_audit_envelope_fields(),
            ),
            uow=uow,
        )
        return command_id


class EventPublisher(IEventPublisher):
    def __init__(
        self,
        *,
        service: Service | None = None,
        feature_environment: str | None = None,
    ) -> None:
        self._service = service or Service(os.environ["SERVICE"])
        self._feature_environment = feature_environment or os.getenv("FEATURE_ENVIRONMENT", "")
        self._store: IDocumentStore[Event[Any], OrganizationID, ITransaction] = get_cloud_provider().document_store(
            collection="events",
            model=Event[Any],
            partition_key_type=OrganizationID,
            service=self._service,
            feature_environment=self._feature_environment,
        )

    @property
    def uow(self) -> ITransaction:
        return get_current_uow()

    def __call__(self) -> Self:
        return self

    async def save(
        self, payload: EventPayload, /, *, organization_id: OrganizationID, event_id: EventID | None = None
    ) -> EventID:
        return await self.__write(payload, organization_id=organization_id, event_id=event_id, uow=self.uow)

    async def quick_save(
        self, payload: EventPayload, /, *, organization_id: OrganizationID, event_id: EventID | None = None
    ) -> EventID:
        # Non-transactional publish (direct write, no transaction lease). Use only when the event
        # is the sole write of the operation -- there is no aggregate to keep atomic with it.
        return await self.__write(payload, organization_id=organization_id, event_id=event_id, uow=None)

    async def __write(
        self,
        payload: EventPayload,
        /,
        *,
        organization_id: OrganizationID,
        event_id: EventID | None,
        uow: ITransaction | None,
    ) -> EventID:
        event_id = event_id or EventID()
        await self._store.set(
            document_id=self._store.to_document_id(event_id),
            document_data=Event[Any](
                id=event_id, organization_id=organization_id, payload=payload, **_audit_envelope_fields()
            ),
            uow=uow,
        )
        return event_id
