from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from control_plane.application.ports.blobs import IBlobStore
from control_plane.application.ports.cache import IAsyncCache
from control_plane.application.ports.changefeed import IDocumentChangeFeed
from control_plane.application.ports.documents import IDocumentStore
from control_plane.application.ports.eventbus import IEventBus, IMessageParser
from control_plane.application.ports.identity import IIdentity
from control_plane.application.ports.jobs import IJobRunner
from control_plane.application.ports.logs import ILogReader
from control_plane.application.ports.operators import IOperatorAuth
from control_plane.application.ports.pools import IPoolDriver
from control_plane.application.ports.runtime import IRuntimeContext
from control_plane.application.ports.secrets import ISecretStore
from control_plane.application.ports.taskqueue import ITaskQueue
from control_plane.application.ports.transactions import ITransaction
from control_plane.domain.entities import IEntity
from control_plane.domain.events.base import EventPayload
from control_plane.domain.value_objects.common import Service
from control_plane.domain.value_objects.core import IDValueObject, StringValueObject


@runtime_checkable
class ICloudProvider(Protocol):
    @property
    def name(self) -> str: ...

    def document_store[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject](
        self,
        *,
        collection: str,
        model: type[EntityT],
        partition_key_type: type[PartitionKeyT],
        service: Service | str | None = None,
        feature_environment: str | None = None,
        use_blob_storage: bool = False,
    ) -> IDocumentStore[EntityT, PartitionKeyT, Any]: ...

    def unit_of_work(self) -> AbstractAsyncContextManager[None]: ...

    def current_transaction(self) -> ITransaction: ...

    def change_feed[DataT: BaseModel](self, data_model: type[DataT], /) -> IDocumentChangeFeed[DataT]: ...

    def event_bus(self) -> IEventBus: ...

    def message_parser[DataT: EventPayload](
        self, *, data_models: list[type[DataT]], cache: IAsyncCache, deduplication_ttl_ms: int | None = None
    ) -> IMessageParser[DataT]: ...

    def task_queue(self) -> ITaskQueue: ...

    def blob_store(self, *, service: Service, bucket: str, feature_environment: str | None = None) -> IBlobStore: ...

    def secret_store(self) -> ISecretStore: ...

    def identity(self) -> IIdentity: ...

    def runtime_context(self) -> IRuntimeContext: ...

    def job_runner(self) -> IJobRunner: ...

    def log_reader(self) -> ILogReader: ...

    def operator_auth(self) -> IOperatorAuth: ...

    def pool_driver(self) -> IPoolDriver | None: ...
