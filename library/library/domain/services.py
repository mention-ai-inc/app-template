from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from library.domain.aggregates import Aggregate
from library.domain.events.base import EventPayload
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject


@dataclass
class ChangeSet[
    AggregateT: Aggregate[Any, Any, Any],
    IdentityT: IDValueObject | ModelValueObject | StringValueObject,
    EventT: EventPayload = EventPayload,
]:
    created: list[AggregateT] = field(default_factory=list)
    updated: list[AggregateT] = field(default_factory=list)
    deleted: list[IdentityT] = field(default_factory=list)
    events: Sequence[EventT] = field(default_factory=list)

    def merge(
        self, other: "ChangeSet[AggregateT, IdentityT, EventT]", /, *, prefer: Literal["keep", "delete"]
    ) -> "ChangeSet[AggregateT, IdentityT, EventT]":
        new_created = {
            **{aggregate.id: aggregate for aggregate in self.created},
            **{aggregate.id: aggregate for aggregate in other.created},
        }
        new_updated = {
            **{aggregate.id: aggregate for aggregate in self.updated},
            **{aggregate.id: aggregate for aggregate in other.updated},
        }
        new_deleted = set(self.deleted).union(other.deleted)

        final_created: list[AggregateT] = []
        final_updated: list[AggregateT] = []
        final_deleted: list[IdentityT] = []

        if prefer == "keep":
            for id in new_deleted:
                if id not in new_created and id not in new_updated:
                    final_deleted.append(id)
            final_created = list(new_created.values())
            final_updated = list(new_updated.values())
        else:
            for id, aggregate in new_created.items():
                if id not in new_deleted:
                    final_created.append(aggregate)
            for id, aggregate in new_updated.items():
                if id not in new_deleted:
                    final_updated.append(aggregate)
            final_deleted = list(new_deleted)

        return ChangeSet(
            created=final_created,
            updated=final_updated,
            deleted=final_deleted,
            events=[*self.events, *other.events],
        )
