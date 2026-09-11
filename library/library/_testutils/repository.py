from typing import Any

from library._testutils.unit_of_work import active_transaction
from library.application.errors import ApplicationError, ApplicationErrorType
from library.domain.aggregates import Aggregate
from library.domain.commands.base import Command, CommandPayload
from library.domain.events.base import Event, EventID, EventPayload
from library.domain.repositories import IRepository
from library.domain.services import ChangeSet
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType


class InMemoryRepository[
    AggregateT: Aggregate[Any, Any, Any],
    IdentityT: IDValueObject | ModelValueObject | StringValueObject,
    EventPayloadT: EventPayload,
    CommandPayloadT: CommandPayload,
](IRepository[AggregateT, IdentityT, EventPayloadT, CommandPayloadT]):
    """In-memory `IRepository` for service-level tests.

    Mirrors `library.infrastructure.repository.Repository` semantics:
    - `save()` records the aggregate by `(organization_id, aggregate.id)`, captures
      pending events / commands into `published_events` / `published_commands`, and
      then calls `aggregate.mark_published()` to clear them — matching production,
      where the same call publishes events to Firestore and clears the aggregate's
      pending state so subsequent saves don't re-publish.
    - `get()` returns a deep copy of the stored aggregate, mirroring production's
      fresh deserialization from Firestore (each load yields a fresh instance with
      no pending events/commands).
    - `get()` of a missing aggregate raises `InfrastructureError(NOT_FOUND_ERROR)`.
    - `get()`, `save()`, `delete()`, and `get_all()` require an active `FakeUnitOfWork`, mirroring
      production's `get_current_uow()` requirement. Use `seed()` for test setup and `quick_get()` for
      non-transactional reads (e.g. post-execution assertions).
    - A subclass's custom query method gets the same requirement by calling
      `_guard_transactional_read()`, which it should whenever its production counterpart queries
      with `uow=self.uow`.
    """

    def __init__(self) -> None:
        self._aggregates: dict[tuple[OrganizationID, IdentityT], AggregateT] = {}
        self.published_events: list[Event[EventPayloadT]] = []
        self.published_commands: list[Command[CommandPayloadT]] = []

    async def seed(self, aggregate: AggregateT, /, *, organization_id: OrganizationID) -> None:
        """Persist an aggregate for test setup without a unit of work.

        Mirrors a row that already exists in Firestore: its events / commands were published
        when it was first saved, so the persisted snapshot carries none. Calls `mark_published()`
        to clear the aggregate's pending events / commands, exactly as `save()` does -- so a
        seeded aggregate equals the copy a use case later reads back (`assert saved == aggregate`),
        and never re-publishes a stale creation event when that use case mutates and saves it.
        Unlike `save()`, it does not capture those events into `published_events` (setup is not a
        publish).
        """
        aggregate.mark_published()
        self._aggregates[(organization_id, aggregate.id)] = aggregate

    async def exists(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> bool:
        return (organization_id, aggregate_id) in self._aggregates

    async def list_ids(self, *, organization_id: OrganizationID) -> list[IdentityT]:
        return [aggregate_id for (org, aggregate_id) in self._aggregates if org == organization_id]

    async def get(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT:
        self.__guard_uow()
        self.__guard_read()
        return self.__fetch(aggregate_id, organization_id=organization_id)

    async def quick_get(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT:
        return self.__fetch(aggregate_id, organization_id=organization_id)

    async def quick_get_all(self, *, organization_id: OrganizationID) -> list[AggregateT]:
        return [
            aggregate.model_copy(deep=True)
            for (org, _), aggregate in self._aggregates.items()
            if org == organization_id
        ]

    async def get_many(self, aggregate_ids: list[IdentityT], /, *, organization_id: OrganizationID) -> list[AggregateT]:
        return [await self.get(aggregate_id, organization_id=organization_id) for aggregate_id in aggregate_ids]

    async def get_many_existing(
        self, aggregate_ids: list[IdentityT], /, *, organization_id: OrganizationID
    ) -> list[AggregateT]:
        return [
            await self.get(aggregate_id, organization_id=organization_id)
            for aggregate_id in aggregate_ids
            if (organization_id, aggregate_id) in self._aggregates
        ]

    async def get_all(self, *, organization_id: OrganizationID) -> list[AggregateT]:
        self.__guard_uow()
        self.__guard_read()
        return [
            aggregate.model_copy(deep=True)
            for (org, _), aggregate in self._aggregates.items()
            if org == organization_id
        ]

    async def save(self, aggregate: AggregateT, /) -> None:
        self.__guard_uow()
        self.__record_write()
        self._aggregates[(aggregate.organization_id, aggregate.id)] = aggregate
        self.published_events.extend(aggregate.events)
        self.published_commands.extend(aggregate.commands)
        aggregate.mark_published()

    async def apply_changeset(
        self,
        changeset: ChangeSet[AggregateT, IdentityT, EventPayloadT],
        /,
        *,
        organization_id: OrganizationID,
    ) -> None:
        for aggregate in changeset.created or []:
            await self.save(aggregate)
        for aggregate in changeset.updated or []:
            await self.save(aggregate)
        for aggregate_id in changeset.deleted or []:
            await self.delete(aggregate_id, organization_id=organization_id)
        for event_payload in changeset.events or []:
            self.published_events.append(
                Event[Any](id=EventID(), organization_id=organization_id, payload=event_payload),
            )

    async def delete(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> None:
        self.__guard_uow()
        self.__record_write()
        self._aggregates.pop((organization_id, aggregate_id), None)

    async def quick_delete(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> None:
        if type(self).delete is not InMemoryRepository.delete:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=(
                    f"{type(self).__name__} overrides delete(); quick_delete would bypass that override "
                    "(e.g. outbox event publishing). Use delete() inside a unit_of_work() instead."
                ),
            )
        self._aggregates.pop((organization_id, aggregate_id), None)

    def _guard_transactional_read(self) -> None:
        """Apply the `get()` guards to a subclass's custom query method.

        Call this from any stub method whose production counterpart queries with `uow=self.uow`,
        so the stub fails the same way production does when no unit of work is active (and when the
        read follows a write in the same transaction). Stub methods mirroring a production query
        that omits `uow=` read outside the transaction and must not call this.
        """
        self.__guard_uow()
        self.__guard_read()

    def __fetch(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT:
        try:
            stored = self._aggregates[(organization_id, aggregate_id)]
        except KeyError:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"Aggregate with ID {aggregate_id} not found in organization {organization_id}",
            ) from None
        return stored.model_copy(deep=True)

    def __guard_uow(self) -> None:
        if active_transaction() is None:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message="Unit of work not initialized",
            )

    def __record_write(self) -> None:
        transaction = active_transaction()
        if transaction is not None:
            transaction.has_written = True

    def __guard_read(self) -> None:
        transaction = active_transaction()
        if transaction is not None and transaction.has_written:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=(
                    "Read-after-write inside a unit of work: a repository read ran after a write in the "
                    "same transaction. Firestore forbids this and rejects the transaction at runtime. "
                    "Phase all reads before any writes within the `unit_of_work()` block "
                    "(see .claude/rules/read-after-write.md)."
                ),
            )
