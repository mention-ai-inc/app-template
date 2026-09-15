import os
from typing import Any, Self

from library.application.ports.documents import IDocumentStore
from library.application.ports.transactions import ITransaction
from library.domain.aggregates import Aggregate
from library.domain.audit.action import AuditAction
from library.domain.audit.diff import diff_aggregate
from library.domain.commands.base import CommandPayload
from library.domain.events.base import Event, EventPayload
from library.domain.repositories import IRepository
from library.domain.services import ChangeSet
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.audit.publisher import AuditEventPublisher
from library.infrastructure.audit.snapshot import recall, remember
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.outbox import CommandDispatcher, EventPublisher
from library.infrastructure.unit_of_work import get_current_uow
from library.providers.registry import get_cloud_provider


class Repository[
    AggregateT: Aggregate[Any, Any, Any],
    IdentityT: IDValueObject | ModelValueObject | StringValueObject,
    EventPayloadT: EventPayload,
    CommandPayloadT: CommandPayload,
](IRepository[AggregateT, IdentityT, EventPayloadT, CommandPayloadT]):
    def __init__(
        self,
        *,
        aggregate: type[AggregateT],
        identity_type: type[IdentityT],
        use_storage: bool = False,
        service: Service | None = None,
        feature_environment: str | None = None,
    ) -> None:
        self._aggregate = aggregate
        self._service = service or Service(os.environ["SERVICE"])
        self._feature_environment = feature_environment or os.getenv("FEATURE_ENVIRONMENT", "")
        self._identity_type = identity_type
        provider = get_cloud_provider()
        self._event_stores = {
            model: provider.document_store(
                collection="events",
                model=Event[model],
                partition_key_type=OrganizationID,
                service=service,
                feature_environment=feature_environment,
            )
            for model in aggregate.event_types()
        }
        self._command_dispatcher = CommandDispatcher(
            service=service,
            feature_environment=feature_environment,
        )
        self._event_publisher = EventPublisher(
            service=service,
            feature_environment=feature_environment,
        )
        self._audit_publisher = AuditEventPublisher(
            service=service,
            feature_environment=feature_environment,
        )

        self._aggregate_store: IDocumentStore[AggregateT, OrganizationID, ITransaction] = provider.document_store(
            collection=aggregate.get_table_name(),
            model=aggregate,
            partition_key_type=OrganizationID,
            service=service,
            feature_environment=feature_environment,
            use_blob_storage=use_storage,
        )

    @property
    def uow(self) -> ITransaction:
        return get_current_uow()

    def __call__(self) -> Self:
        return self

    async def exists(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> bool:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            document_id = store.to_document_id(aggregate_id)
            return await store.exists(document_id=document_id)

    async def list_ids(self, *, organization_id: OrganizationID) -> list[IdentityT]:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            document_ids = await store.query_ids()

        if issubclass(self._identity_type, ModelValueObject):
            return [self._identity_type.from_id(id=document_id) for document_id in document_ids]
        else:
            return [self._identity_type(document_id) for document_id in document_ids]

    async def get(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            document_id = store.to_document_id(aggregate_id)
            document = await store.get(document_id=document_id, uow=self.uow)
        remember(document, document_id=document_id)
        return document

    async def get_many(self, aggregate_ids: list[IdentityT], /, *, organization_id: OrganizationID) -> list[AggregateT]:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            documents = await store.get_many(
                document_ids=[store.to_document_id(aggregate_id) for aggregate_id in aggregate_ids],
                uow=self.uow,
            )
        self.__remember_all(documents)
        return documents

    async def get_many_existing(
        self, aggregate_ids: list[IdentityT], /, *, organization_id: OrganizationID
    ) -> list[AggregateT]:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            documents = await store.get_many(
                document_ids=[store.to_document_id(aggregate_id) for aggregate_id in aggregate_ids],
                uow=self.uow,
                ignore_missing=True,
            )
        self.__remember_all(documents)
        return documents

    async def get_all(self, *, organization_id: OrganizationID) -> list[AggregateT]:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            documents = await store.query(mode="deep", uow=self.uow)
        self.__remember_all(documents.entities)
        return documents.entities

    async def quick_get(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            document_id = store.to_document_id(aggregate_id)
            document = await store.get(document_id=document_id)
        remember(document, document_id=document_id)
        return document

    async def save(self, aggregate: AggregateT, /) -> None:
        with self._aggregate_store.connect_to_partition(aggregate.organization_id) as store:
            document_id = store.to_document_id(aggregate.id)
            await store.set(document_id=document_id, document_data=aggregate, uow=self.uow)

        for event in aggregate.events:
            await self._event_publisher.save(
                event.payload, organization_id=aggregate.organization_id, event_id=event.id
            )
        for command in aggregate.commands:
            await self._command_dispatcher.save(
                command.payload,
                organization_id=aggregate.organization_id,
                command_id=command.id,
                delay_seconds=command.delay_seconds,
            )
        await self.__record_audit_save(aggregate, document_id=document_id)
        aggregate.mark_published()

    async def delete(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> None:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            document_id = store.to_document_id(aggregate_id)
            await store.delete(document_id=document_id, uow=self.uow)

        await self._audit_publisher.save(
            action=AuditAction.DELETED,
            resource_type=self._aggregate.__name__,
            resource_id=document_id,
            organization_id=organization_id,
            changes=None,
        )

    async def quick_delete(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> None:
        # Non-transactional delete (direct write, no transaction lease). Only valid for a plain
        # single-document delete. Refuse the two cases where bypassing the transaction would silently
        # lose correctness, turning a hard-to-spot bug into a loud error at the first call:
        #   1. a subclass overrides delete() -- its custom logic (typically publishing a deletion event
        #      as part of the atomic outbox) would be skipped entirely.
        #   2. the aggregate has subcollections -- the parent + child deletes would not be atomic.
        if type(self).delete is not Repository.delete:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=(
                    f"{type(self).__name__} overrides delete(); quick_delete would bypass that override "
                    "(e.g. outbox event publishing). Use delete() inside a unit_of_work() instead."
                ),
            )
        if self._aggregate.get_subentity_names():
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=(
                    f"{self._aggregate.__name__} has subcollections; quick_delete's cascade would not be "
                    "atomic. Use delete() inside a unit_of_work() instead."
                ),
            )
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            document_id = store.to_document_id(aggregate_id)
            await store.delete(document_id=document_id, uow=None)

    async def apply_changeset(
        self, changeset: ChangeSet[AggregateT, IdentityT, EventPayloadT], /, *, organization_id: OrganizationID
    ) -> None:
        for aggregate in changeset.created or []:
            await self.save(aggregate)
        for aggregate in changeset.updated or []:
            await self.save(aggregate)
        for aggregate_id in changeset.deleted or []:
            await self.delete(aggregate_id, organization_id=organization_id)
        for event in changeset.events or []:
            await self._event_publisher.save(event, organization_id=organization_id)

    def __remember_all(self, aggregates: list[AggregateT], /) -> None:
        for aggregate in aggregates:
            remember(aggregate, document_id=self._aggregate_store.to_document_id(aggregate.id))

    async def __record_audit_save(self, aggregate: AggregateT, /, *, document_id: str) -> None:
        before = recall(type(aggregate), organization_id=aggregate.organization_id, document_id=document_id)
        if before is None:
            action = AuditAction.CREATED
            changes = None
        else:
            action = AuditAction.UPDATED
            changes = diff_aggregate(before, aggregate)
            if not changes:
                return

        await self._audit_publisher.save(
            action=action,
            resource_type=type(aggregate).__name__,
            resource_id=document_id,
            organization_id=aggregate.organization_id,
            changes=changes,
        )
