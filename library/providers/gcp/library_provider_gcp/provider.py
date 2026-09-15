from contextlib import AbstractAsyncContextManager
from typing import Any

from pydantic import BaseModel

from library.application.ports.cache import IAsyncCache
from library.application.ports.documents import IDocumentStore
from library.domain.entities import IEntity
from library.domain.events.base import EventPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, StringValueObject
from library.infrastructure.cloud.pubsub import Pubsub
from library.infrastructure.cloud.secretmanager import SecretManager
from library.infrastructure.cloud.tasks import Tasks
from library.infrastructure.persistence.storage import BucketName
from library_provider_gcp.blobs import ServiceBucket
from library_provider_gcp.changefeed import FirestoreDocument
from library_provider_gcp.events import PubSubMessageParser
from library_provider_gcp.firestorage import FireStorage
from library_provider_gcp.firestore import UOW, Firestore
from library_provider_gcp.identity import GcpIdentity, GcpRuntimeContext
from library_provider_gcp.unit_of_work import gcp_unit_of_work, get_current_gcp_transaction


class GcpProvider:
    @property
    def name(self) -> str:
        return "gcp"

    def document_store[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject](
        self,
        *,
        collection: str,
        model: type[EntityT],
        partition_key_type: type[PartitionKeyT],
        service: Service | str | None = None,
        feature_environment: str | None = None,
        use_blob_storage: bool = False,
    ) -> IDocumentStore[EntityT, PartitionKeyT, Any]:
        if use_blob_storage:
            return FireStorage(
                collection=collection,
                model=model,
                partition_key_type=partition_key_type,
                service=service,
                feature_environment=feature_environment,
            )
        return Firestore(
            collection=collection,
            model=model,
            partition_key_type=partition_key_type,
            service=service,
            feature_environment=feature_environment,
        )

    def unit_of_work(self) -> AbstractAsyncContextManager[None]:
        return gcp_unit_of_work()

    def current_transaction(self) -> UOW:
        return get_current_gcp_transaction()

    def change_feed[DataT: BaseModel](self, data_model: type[DataT], /) -> FirestoreDocument[DataT]:
        return FirestoreDocument(data_model)

    def event_bus(self) -> Pubsub:
        return Pubsub()

    def message_parser[DataT: EventPayload](
        self, *, data_models: list[type[DataT]], cache: IAsyncCache, deduplication_ttl_ms: int | None = None
    ) -> PubSubMessageParser[DataT]:
        return PubSubMessageParser(data_models=data_models, cache=cache, deduplication_ttl_ms=deduplication_ttl_ms)

    def task_queue(self) -> Tasks:
        return Tasks()

    def blob_store(self, *, service: Service, bucket: str, feature_environment: str | None = None) -> ServiceBucket:
        return ServiceBucket(service=service, bucket=BucketName(bucket), feature_environment=feature_environment)

    def secret_store(self) -> SecretManager:
        return SecretManager()

    def identity(self) -> GcpIdentity:
        return GcpIdentity()

    def runtime_context(self) -> GcpRuntimeContext:
        return GcpRuntimeContext()


PROVIDER = GcpProvider()
