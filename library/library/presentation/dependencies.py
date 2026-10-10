from control_plane.application.ports.unit_of_work import IUnitOfWork
from control_plane.infrastructure.unit_of_work import unit_of_work
from control_plane.presentation.dependencies import (
    get_cache,
    get_event_bus,
    get_message_parser,
    get_task_queue,
    get_users_client,
)
from library.domain.outbox import ICommandDispatcher, IEventPublisher
from library.infrastructure.outbox import CommandDispatcher, EventPublisher

__all__ = [
    "get_cache",
    "get_command_dispatcher",
    "get_event_bus",
    "get_event_publisher",
    "get_message_parser",
    "get_task_queue",
    "get_unit_of_work",
    "get_users_client",
]


def get_event_publisher() -> IEventPublisher:
    return EventPublisher()


def get_command_dispatcher() -> ICommandDispatcher:
    return CommandDispatcher()


def get_unit_of_work() -> IUnitOfWork:
    return lambda: unit_of_work()
