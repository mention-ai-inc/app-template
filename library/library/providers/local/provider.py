from contextlib import AbstractAsyncContextManager
from typing import Any

from fastapi import Request
from pydantic import BaseModel, ValidationError

from library.application.ports.cache import IAsyncCache
from library.application.ports.documents import IDocumentStore
from library.application.ports.pools import IPoolDriver
from library.domain.entities import IEntity
from library.domain.events.base import EventPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, StringValueObject
from library.providers.local.database import LocalTransaction
from library.providers.local.documents import LocalDocumentStore
from library.providers.local.events import LocalMessageParser
from library.providers.local.messaging import LocalEventBus, LocalTaskQueue
from library.providers.local.storage import LocalBlobStore, LocalIdentity, LocalRuntimeContext, LocalSecretStore
from library.providers.local.unit_of_work import get_current_local_transaction, local_unit_of_work


class LocalDocumentChangeFeed[DataT: BaseModel]:
    def __init__(self, data_model: type[DataT], /) -> None:
        self._data_model = data_model

    async def __call__(self, request: Request) -> DataT | None:
        try:
            return self._data_model.model_validate(await request.json())
        except (ValidationError, ValueError):
            return None


class LocalProvider:
    def __init__(self) -> None:
        self._event_bus = LocalEventBus()
        self._task_queue = LocalTaskQueue()
        self._secret_store = LocalSecretStore()
        self._identity = LocalIdentity()
        self._runtime_context = LocalRuntimeContext()
        self._blob_stores: dict[str, LocalBlobStore] = {}

    @property
    def name(self) -> str:
        return "local"

    def document_store[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject](
        self,
        *,
        collection: str,
        model: type[EntityT],
        partition_key_type: type[PartitionKeyT],
        service: Service | str | None = None,
        feature_environment: str | None = None,
        use_blob_storage: bool = False,  # noqa: ARG002
    ) -> IDocumentStore[EntityT, PartitionKeyT, Any]:
        return LocalDocumentStore(
            collection=collection,
            model=model,
            partition_key_type=partition_key_type,
            service=service,
            feature_environment=feature_environment,
        )

    def unit_of_work(self) -> AbstractAsyncContextManager[None]:
        return local_unit_of_work()

    def current_transaction(self) -> LocalTransaction:
        return get_current_local_transaction()

    def change_feed[DataT: BaseModel](self, data_model: type[DataT], /) -> LocalDocumentChangeFeed[DataT]:
        return LocalDocumentChangeFeed(data_model)

    def event_bus(self) -> LocalEventBus:
        return self._event_bus

    def message_parser[DataT: EventPayload](
        self, *, data_models: list[type[DataT]], cache: IAsyncCache, deduplication_ttl_ms: int | None = None
    ) -> LocalMessageParser[DataT]:
        return LocalMessageParser(data_models=data_models, cache=cache, deduplication_ttl_ms=deduplication_ttl_ms)

    def task_queue(self) -> LocalTaskQueue:
        return self._task_queue

    def blob_store(self, *, service: Service, bucket: str, feature_environment: str | None = None) -> LocalBlobStore:
        name = f"{feature_environment or ''}{service.value}-{bucket}"
        return self._blob_stores.setdefault(name, LocalBlobStore(bucket=name))

    def secret_store(self) -> LocalSecretStore:
        return self._secret_store

    def identity(self) -> LocalIdentity:
        return self._identity

    def runtime_context(self) -> LocalRuntimeContext:
        return self._runtime_context

    def pool_driver(self) -> IPoolDriver | None:
        return None


PROVIDER = LocalProvider()
