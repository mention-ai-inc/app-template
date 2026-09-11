from typing import Any

from library.domain.events.base import Event, EventID, EventPayload
from library.domain.outbox import IEventPublisher
from library.domain.value_objects.users import OrganizationID


class FakeEventPublisher(IEventPublisher):
    """In-memory `IEventPublisher`.

    Captures every saved event into `saved_events` so tests can assert on
    the published payload and organization.
    """

    def __init__(self) -> None:
        self.saved_events: list[Event[Any]] = []

    async def save(
        self,
        payload: EventPayload,
        /,
        *,
        organization_id: OrganizationID,
        event_id: EventID | None = None,
    ) -> EventID:
        event_id = event_id or EventID()
        self.saved_events.append(
            Event[Any](id=event_id, organization_id=organization_id, payload=payload),
        )
        return event_id

    async def quick_save(
        self,
        payload: EventPayload,
        /,
        *,
        organization_id: OrganizationID,
        event_id: EventID | None = None,
    ) -> EventID:
        return await self.save(payload, organization_id=organization_id, event_id=event_id)
