from typing import Any

from library.application.ports.blobs import IBlobStore
from library.application.ports.changefeed import IDocumentChangeFeed
from library.application.ports.documents import IDocumentStore
from library.application.ports.eventbus import IEventBus
from library.application.ports.identity import IIdentity
from library.application.ports.pools import IPoolDriver
from library.application.ports.provider import ICloudProvider
from library.application.ports.runtime import IRuntimeContext
from library.application.ports.secrets import ISecretStore
from library.application.ports.taskqueue import ITaskQueue
from library_provider_azure.blobs import BlobContainer
from library_provider_azure.changefeed import CosmosChangeFeedItem
from library_provider_azure.documents import CosmosDocumentStore
from library_provider_azure.identity import AzureIdentity, AzureRuntimeContext
from library_provider_azure.messaging import ServiceBusEventBus, ServiceBusTaskQueue
from library_provider_azure.pools import AzurePoolDriver
from library_provider_azure.provider import AzureProvider
from library_provider_azure.secrets import KeyVaultSecretStore
from library_provider_azure.transactions import CosmosTransaction


def test_the_azure_adapters_satisfy_their_ports() -> None:
    document_store: type[IDocumentStore[Any, Any, CosmosTransaction]] = CosmosDocumentStore
    event_bus: type[IEventBus] = ServiceBusEventBus
    task_queue: type[ITaskQueue] = ServiceBusTaskQueue
    secret_store: type[ISecretStore] = KeyVaultSecretStore
    blob_store: type[IBlobStore] = BlobContainer
    identity: type[IIdentity] = AzureIdentity
    runtime_context: type[IRuntimeContext] = AzureRuntimeContext
    change_feed: type[IDocumentChangeFeed[Any]] = CosmosChangeFeedItem
    pool_driver: type[IPoolDriver] = AzurePoolDriver

    assert (
        len(
            {
                document_store,
                event_bus,
                task_queue,
                secret_store,
                blob_store,
                identity,
                runtime_context,
                change_feed,
                pool_driver,
            }
        )
        == 9
    )


def test_the_azure_provider_satisfies_the_provider_port() -> None:
    provider: ICloudProvider = AzureProvider()

    assert provider.name == "azure"


def test_the_azure_provider_returns_a_pool_driver_because_service_bus_cannot_push() -> None:
    assert AzureProvider().pool_driver() is not None
