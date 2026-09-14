from typing import Any

from library.application.ports.blobs import IBlobStore
from library.application.ports.documents import IDocumentStore
from library.application.ports.eventbus import IEventBus
from library.application.ports.secrets import ISecretStore
from library.application.ports.taskqueue import ITaskQueue
from library.infrastructure.cloud.pubsub import Pubsub
from library.infrastructure.cloud.secretmanager import SecretManager
from library.infrastructure.cloud.tasks import Tasks
from library.infrastructure.persistence.firestore import UOW, Firestore
from library.infrastructure.persistence.storage import ServiceBucket


def test_the_gcp_adapters_satisfy_their_ports() -> None:
    document_store: type[IDocumentStore[Any, Any, UOW]] = Firestore
    event_bus: type[IEventBus] = Pubsub
    task_queue: type[ITaskQueue] = Tasks
    secret_store: type[ISecretStore] = SecretManager
    blob_store: type[IBlobStore] = ServiceBucket

    assert len({document_store, event_bus, task_queue, secret_store, blob_store}) == 5
