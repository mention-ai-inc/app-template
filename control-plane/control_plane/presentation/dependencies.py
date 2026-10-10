from control_plane.application.ports.eventbus import IEventBus, IMessageParser
from control_plane.application.ports.taskqueue import ITaskQueue
from control_plane.application.ports.users import IUsersClient
from control_plane.domain.events.base import EventPayload
from control_plane.infrastructure.persistence.cache.base import AsyncCache
from control_plane.infrastructure.users import ClerkClient
from control_plane.providers.registry import get_cloud_provider


def get_users_client() -> IUsersClient:
    return ClerkClient()


def get_cache() -> AsyncCache:
    return AsyncCache()


def get_event_bus() -> IEventBus:
    return get_cloud_provider().event_bus()


def get_task_queue() -> ITaskQueue:
    return get_cloud_provider().task_queue()


def get_message_parser[DataT: EventPayload](*, data_models: list[type[DataT]]) -> IMessageParser[DataT]:
    return get_cloud_provider().message_parser(data_models=data_models, cache=get_cache())
