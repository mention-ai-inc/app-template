import os
from datetime import UTC, datetime
from types import UnionType
from typing import get_args

from library.domain.commands.base import Command, CommandPayload
from library.domain.entities import Entity
from library.domain.events.base import Event, EventPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import EnumValueObject, IDValueObject, ModelValueObject, StringValueObject
from library.domain.value_objects.users import OrganizationID


class Aggregate[
    IdentityT: IDValueObject | ModelValueObject | StringValueObject | EnumValueObject,
    EventPayloadT: EventPayload,
    CommandPayloadT: CommandPayload,
](Entity[IdentityT]):
    organization_id: OrganizationID
    _events: set[Event[EventPayloadT]] = set()
    _commands: set[Command[CommandPayloadT]] = set()

    @classmethod
    def get_table_name(cls) -> str:
        return cls.__name__.lower()

    @property
    def events(self) -> list[Event[EventPayloadT]]:
        return list(self._events)

    @property
    def commands(self) -> list[Command[CommandPayloadT]]:
        return list(self._commands)

    @classmethod
    def event_types(cls) -> list[type[EventPayloadT]]:  # yeesh
        event_types = cls.__mro__[1].__pydantic_generic_metadata__["args"][1]
        if event_types is EventPayload:
            return []
        elif isinstance(event_types, UnionType):
            return list(get_args(event_types))
        else:
            return [event_types]

    @classmethod
    def command_types(cls) -> list[type[CommandPayloadT]]:  # yeesh
        command_types = cls.__mro__[1].__pydantic_generic_metadata__["args"][2]
        if command_types is CommandPayload:
            return []
        elif isinstance(command_types, UnionType):
            return list(get_args(command_types))
        else:
            return [command_types]

    def add_event(self, payload: EventPayloadT, /) -> None:
        event = Event[type(payload)](payload=payload, organization_id=self.organization_id)
        self._events.add(event)

    def add_command(
        self,
        payload: CommandPayloadT,
        /,
        *,
        delay_seconds: int = 0,
        service: Service | None = None,
    ) -> None:
        command = Command[type(payload)](
            payload=payload,
            organization_id=self.organization_id,
            delay_seconds=delay_seconds,
            created_at=datetime.now(UTC),
            service=service or Service(os.environ["SERVICE"]),
        )
        self._commands.add(command)

    def mark_published(self) -> None:
        """Clear pending events and commands. Called by the repository after `save()`
        has successfully published them, so subsequent saves of the same aggregate
        within a single request don't re-publish already-handled events."""
        self._events.clear()
        self._commands.clear()
