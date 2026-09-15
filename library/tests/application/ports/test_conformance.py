from typing import Any

from library.application.ports.blobs import IBlobStore
from library.application.ports.documents import IDocumentStore
from library.application.ports.eventbus import IEventBus
from library.application.ports.identity import IIdentity
from library.application.ports.jobs import IJobRunner
from library.application.ports.logs import ILogReader
from library.application.ports.operators import IOperatorAuth
from library.application.ports.provider import ICloudProvider
from library.application.ports.runtime import IRuntimeContext
from library.application.ports.secrets import ISecretStore
from library.application.ports.taskqueue import ITaskQueue
from library.providers.local.documents import LocalDocumentStore
from library.providers.local.jobs import LocalJobRunner, LocalLogReader
from library.providers.local.messaging import LocalEventBus, LocalTaskQueue
from library.providers.local.operators import LocalOperatorAuth
from library.providers.local.provider import LocalProvider
from library.providers.local.storage import LocalBlobStore, LocalIdentity, LocalRuntimeContext, LocalSecretStore


def test_the_local_adapters_satisfy_their_ports() -> None:
    document_store: type[IDocumentStore[Any, Any, Any]] = LocalDocumentStore
    event_bus: type[IEventBus] = LocalEventBus
    task_queue: type[ITaskQueue] = LocalTaskQueue
    secret_store: type[ISecretStore] = LocalSecretStore
    blob_store: type[IBlobStore] = LocalBlobStore
    identity: type[IIdentity] = LocalIdentity
    runtime_context: type[IRuntimeContext] = LocalRuntimeContext
    job_runner: type[IJobRunner] = LocalJobRunner
    log_reader: type[ILogReader] = LocalLogReader
    operator_auth: type[IOperatorAuth] = LocalOperatorAuth

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
                job_runner,
                log_reader,
                operator_auth,
            }
        )
        == 10
    )


def test_the_local_provider_satisfies_the_provider_port() -> None:
    provider: ICloudProvider = LocalProvider()

    assert provider.name == "local"
