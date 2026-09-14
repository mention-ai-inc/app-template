from library.application.events import MessageParser
from library.application.ports.unit_of_work import IUnitOfWork
from library.application.ports.users import IUsersClient
from library.domain.events.base import EventPayload
from library.domain.outbox import ICommandDispatcher, IEventPublisher
from library.infrastructure.outbox import CommandDispatcher, EventPublisher
from library.infrastructure.persistence.cache.base import AsyncCache
from library.infrastructure.unit_of_work import unit_of_work
from library.infrastructure.users import ClerkClient


def get_users_client() -> IUsersClient:
    return ClerkClient()


def get_cache() -> AsyncCache:
    return AsyncCache()


def get_event_publisher() -> IEventPublisher:
    return EventPublisher()


def get_command_dispatcher() -> ICommandDispatcher:
    return CommandDispatcher()


def get_unit_of_work() -> IUnitOfWork:
    return lambda: unit_of_work()


def get_message_parser[DataT: EventPayload](*, data_models: list[type[DataT]]) -> MessageParser[DataT]:
    return MessageParser(data_models=data_models, cache=get_cache())
