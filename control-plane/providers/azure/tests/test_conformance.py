from typing import Any

from control_plane.application.ports.blobs import IBlobStore
from control_plane.application.ports.changefeed import IDocumentChangeFeed
from control_plane.application.ports.documents import IDocumentStore
from control_plane.application.ports.eventbus import IEventBus
from control_plane.application.ports.identity import IIdentity
from control_plane.application.ports.jobs import IJobRunner
from control_plane.application.ports.logs import ILogReader
from control_plane.application.ports.operators import IOperatorAuth
from control_plane.application.ports.pools import IPoolDriver
from control_plane.application.ports.provider import ICloudProvider
from control_plane.application.ports.runtime import IRuntimeContext
from control_plane.application.ports.secrets import ISecretStore
from control_plane.application.ports.taskqueue import ITaskQueue
from control_plane_provider_azure.blobs import BlobContainer
from control_plane_provider_azure.changefeed import CosmosChangeFeedItem
from control_plane_provider_azure.documents import CosmosDocumentStore
from control_plane_provider_azure.identity import AzureIdentity, AzureRuntimeContext
from control_plane_provider_azure.jobs import ContainerAppJobRunner
from control_plane_provider_azure.logs import LogAnalyticsReader
from control_plane_provider_azure.messaging import ServiceBusEventBus, ServiceBusTaskQueue
from control_plane_provider_azure.operators import EasyAuthOperatorAuth
from control_plane_provider_azure.pools import AzurePoolDriver
from control_plane_provider_azure.provider import AzureProvider
from control_plane_provider_azure.secrets import KeyVaultSecretStore
from control_plane_provider_azure.transactions import CosmosTransaction


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
    job_runner: type[IJobRunner] = ContainerAppJobRunner
    log_reader: type[ILogReader] = LogAnalyticsReader
    operator_auth: type[IOperatorAuth] = EasyAuthOperatorAuth

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
                job_runner,
                log_reader,
                operator_auth,
            }
        )
        == 12
    )


def test_the_azure_provider_satisfies_the_provider_port() -> None:
    provider: ICloudProvider = AzureProvider()

    assert provider.name == "azure"


def test_the_azure_provider_returns_a_pool_driver_because_service_bus_cannot_push() -> None:
    assert AzureProvider().pool_driver() is not None
