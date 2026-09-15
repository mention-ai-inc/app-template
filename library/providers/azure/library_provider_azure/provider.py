from contextlib import AbstractAsyncContextManager
from typing import Any

from pydantic import BaseModel

from library.application.ports.cache import IAsyncCache
from library.application.ports.documents import IDocumentStore
from library.domain.entities import IEntity
from library.domain.events.base import EventPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, StringValueObject
from library.infrastructure.persistence.storage import BucketName
from library_provider_azure.blobs import BlobContainer
from library_provider_azure.changefeed import CosmosChangeFeedItem
from library_provider_azure.documents import CosmosDocumentStore
from library_provider_azure.events import ServiceBusMessageParser
from library_provider_azure.identity import AzureIdentity, AzureRuntimeContext
from library_provider_azure.jobs import ContainerAppJobRunner
from library_provider_azure.logs import LogAnalyticsReader
from library_provider_azure.messaging import ServiceBusEventBus, ServiceBusTaskQueue
from library_provider_azure.operators import EasyAuthOperatorAuth
from library_provider_azure.pools import AzurePoolDriver
from library_provider_azure.secrets import KeyVaultSecretStore
from library_provider_azure.transactions import CosmosTransaction
from library_provider_azure.unit_of_work import azure_unit_of_work, get_current_azure_transaction


class AzureProvider:
    def __init__(self) -> None:
        self._job_runner = ContainerAppJobRunner()
        self._log_reader = LogAnalyticsReader(job_runner=self._job_runner)
        self._operator_auth = EasyAuthOperatorAuth()

    @property
    def name(self) -> str:
        return "azure"

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
        return CosmosDocumentStore(
            collection=collection,
            model=model,
            partition_key_type=partition_key_type,
            service=service,
            feature_environment_override=feature_environment,
        )

    def unit_of_work(self) -> AbstractAsyncContextManager[None]:
        return azure_unit_of_work()

    def current_transaction(self) -> CosmosTransaction:
        return get_current_azure_transaction()

    def change_feed[DataT: BaseModel](self, data_model: type[DataT], /) -> CosmosChangeFeedItem[DataT]:
        return CosmosChangeFeedItem(data_model)

    def event_bus(self) -> ServiceBusEventBus:
        return ServiceBusEventBus()

    def message_parser[DataT: EventPayload](
        self, *, data_models: list[type[DataT]], cache: IAsyncCache, deduplication_ttl_ms: int | None = None
    ) -> ServiceBusMessageParser[DataT]:
        return ServiceBusMessageParser(data_models=data_models, cache=cache, deduplication_ttl_ms=deduplication_ttl_ms)

    def task_queue(self) -> ServiceBusTaskQueue:
        return ServiceBusTaskQueue()

    def blob_store(self, *, service: Service, bucket: str, feature_environment: str | None = None) -> BlobContainer:
        return BlobContainer(
            service=service, bucket=BucketName(bucket), feature_environment_override=feature_environment
        )

    def secret_store(self) -> KeyVaultSecretStore:
        return KeyVaultSecretStore()

    def identity(self) -> AzureIdentity:
        return AzureIdentity()

    def runtime_context(self) -> AzureRuntimeContext:
        return AzureRuntimeContext()

    def job_runner(self) -> ContainerAppJobRunner:
        return self._job_runner

    def log_reader(self) -> LogAnalyticsReader:
        return self._log_reader

    def operator_auth(self) -> EasyAuthOperatorAuth:
        return self._operator_auth

    def pool_driver(self) -> AzurePoolDriver:
        return AzurePoolDriver()


PROVIDER = AzureProvider()
