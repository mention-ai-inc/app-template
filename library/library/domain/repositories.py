from typing import Any

from library.domain.aggregates import Aggregate
from library.domain.commands.base import CommandPayload
from library.domain.events.base import EventPayload
from library.domain.services import ChangeSet
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject
from library.domain.value_objects.users import OrganizationID


class IRepository[
    AggregateT: Aggregate[Any, Any, Any],
    IdentityT: IDValueObject | ModelValueObject | StringValueObject,
    EventPayloadT: EventPayload,
    CommandPayloadT: CommandPayload,
]:
    async def exists(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> bool: ...

    async def list_ids(self, *, organization_id: OrganizationID) -> list[IdentityT]: ...

    async def get(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT: ...

    async def get_many(
        self, aggregate_ids: list[IdentityT], /, *, organization_id: OrganizationID
    ) -> list[AggregateT]: ...

    async def get_many_existing(
        self, aggregate_ids: list[IdentityT], /, *, organization_id: OrganizationID
    ) -> list[AggregateT]: ...

    async def get_all(self, *, organization_id: OrganizationID) -> list[AggregateT]: ...

    async def quick_get(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> AggregateT: ...

    async def save(self, aggregate: AggregateT, /) -> None: ...

    async def apply_changeset(
        self, changeset: ChangeSet[AggregateT, IdentityT, EventPayloadT], /, *, organization_id: OrganizationID
    ) -> None: ...

    async def delete(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> None: ...

    async def quick_delete(self, aggregate_id: IdentityT, /, *, organization_id: OrganizationID) -> None: ...
