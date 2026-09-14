from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from library.application.ports.blobs import IBlobStore
from library.application.ports.changefeed import IDocumentChangeFeed
from library.application.ports.documents import IDocumentStore
from library.application.ports.eventbus import IEventBus
from library.application.ports.identity import IIdentity
from library.application.ports.runtime import IRuntimeContext
from library.application.ports.secrets import ISecretStore
from library.application.ports.taskqueue import ITaskQueue
from library.application.ports.transactions import ITransaction
from library.domain.entities import IEntity
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, StringValueObject


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

    def task_queue(self) -> ITaskQueue: ...

    def blob_store(self, *, service: Service, bucket: str, feature_environment: str | None = None) -> IBlobStore: ...

    def secret_store(self) -> ISecretStore: ...

    def identity(self) -> IIdentity: ...

    def runtime_context(self) -> IRuntimeContext: ...
