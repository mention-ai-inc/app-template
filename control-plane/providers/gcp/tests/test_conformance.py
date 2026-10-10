from typing import Any

from control_plane.application.ports.blobs import IBlobStore
from control_plane.application.ports.documents import IDocumentStore
from control_plane.application.ports.eventbus import IEventBus
from control_plane.application.ports.jobs import IJobRunner
from control_plane.application.ports.logs import ILogReader
from control_plane.application.ports.operators import IOperatorAuth
from control_plane.application.ports.provider import ICloudProvider
from control_plane.application.ports.secrets import ISecretStore
from control_plane.application.ports.taskqueue import ITaskQueue
from control_plane_provider_gcp.blobs import ServiceBucket
from control_plane_provider_gcp.cloud.pubsub import Pubsub
from control_plane_provider_gcp.cloud.secretmanager import SecretManager
from control_plane_provider_gcp.cloud.tasks import Tasks
from control_plane_provider_gcp.firestorage import FireStorage
from control_plane_provider_gcp.firestore import UOW, Firestore
from control_plane_provider_gcp.jobs import CloudRunJobRunner
from control_plane_provider_gcp.logs import CloudLoggingReader
from control_plane_provider_gcp.operators import IapOperatorAuth
from control_plane_provider_gcp.provider import GcpProvider


def test_the_gcp_adapters_satisfy_their_ports() -> None:
    document_store: type[IDocumentStore[Any, Any, UOW]] = Firestore
    blob_backed_document_store: type[IDocumentStore[Any, Any, UOW]] = FireStorage
    event_bus: type[IEventBus] = Pubsub
    task_queue: type[ITaskQueue] = Tasks
    secret_store: type[ISecretStore] = SecretManager
    blob_store: type[IBlobStore] = ServiceBucket
    job_runner: type[IJobRunner] = CloudRunJobRunner
    log_reader: type[ILogReader] = CloudLoggingReader
    operator_auth: type[IOperatorAuth] = IapOperatorAuth

    assert (
        len(
            {
                document_store,
                blob_backed_document_store,
                event_bus,
                task_queue,
                secret_store,
                blob_store,
                job_runner,
                log_reader,
                operator_auth,
            }
        )
        == 9
    )


def test_the_gcp_provider_satisfies_the_provider_port() -> None:
    provider: ICloudProvider = GcpProvider()

    assert provider.name == "gcp"
