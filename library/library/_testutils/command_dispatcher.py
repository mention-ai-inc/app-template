from typing import Any

from library.domain.commands.base import Command, CommandID, CommandPayload
from library.domain.outbox import ICommandDispatcher
from library.domain.value_objects.users import OrganizationID


class FakeCommandDispatcher(ICommandDispatcher):
    """In-memory `ICommandDispatcher`.

    Captures every saved command into `saved_commands` so tests can assert on
    the dispatched payload, organization, and delay.
    """

    def __init__(self) -> None:
        self.saved_commands: list[Command[Any]] = []

    async def save(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None = None,
        delay_seconds: int = 0,
    ) -> CommandID:
        command_id = command_id or CommandID()
        self.saved_commands.append(
            Command[Any](
                id=command_id,
                organization_id=organization_id,
                payload=payload,
                delay_seconds=delay_seconds,
                service=payload.SERVICE,
            )
        )
        return command_id

    async def quick_save(
        self,
        payload: CommandPayload,
        /,
        *,
        organization_id: OrganizationID,
        command_id: CommandID | None = None,
        delay_seconds: int = 0,
    ) -> CommandID:
        return await self.save(
            payload, organization_id=organization_id, command_id=command_id, delay_seconds=delay_seconds
        )
