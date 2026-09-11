from library.domain.commands.base import CommandID, CommandPayload
from library.domain.events.base import EventID, EventPayload
from library.domain.value_objects.users import OrganizationID


class ICommandDispatcher:
    async def save(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None = None,
        delay_seconds: int = 0,
    ) -> CommandID: ...

    async def quick_save(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None = None,
        delay_seconds: int = 0,
    ) -> CommandID: ...


class IEventPublisher:
    async def save(
        self,
        payload: EventPayload,
        /,
        *,
        organization_id: OrganizationID,
        event_id: EventID | None = None,
    ) -> EventID: ...

    async def quick_save(
        self,
        payload: EventPayload,
        /,
        *,
        organization_id: OrganizationID,
        event_id: EventID | None = None,
    ) -> EventID: ...
