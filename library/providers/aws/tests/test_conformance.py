from typing import Any

from library_provider_aws.blobs import S3Bucket
from library_provider_aws.dynamodb import DynamoDbDocumentStore
from library_provider_aws.messaging import SnsEventBus, SqsTaskQueue
from library_provider_aws.pools import SqsPoolDriver
from library_provider_aws.provider import AwsProvider
from library_provider_aws.secrets import SecretsManager
from library_provider_aws.transactions import AwsTransaction

from library.application.ports.blobs import IBlobStore
from library.application.ports.documents import IDocumentStore
from library.application.ports.eventbus import IEventBus
from library.application.ports.pools import IPoolDriver
from library.application.ports.provider import ICloudProvider
from library.application.ports.secrets import ISecretStore
from library.application.ports.taskqueue import ITaskQueue


def test_the_aws_adapters_satisfy_their_ports() -> None:
    document_store: type[IDocumentStore[Any, Any, AwsTransaction]] = DynamoDbDocumentStore
    event_bus: type[IEventBus] = SnsEventBus
    task_queue: type[ITaskQueue] = SqsTaskQueue
    secret_store: type[ISecretStore] = SecretsManager
    blob_store: type[IBlobStore] = S3Bucket
    pool_driver: type[IPoolDriver] = SqsPoolDriver

    assert len({document_store, event_bus, task_queue, secret_store, blob_store, pool_driver}) == 6


def test_the_aws_provider_satisfies_the_provider_port() -> None:
    provider: ICloudProvider = AwsProvider()

    assert provider.name == "aws"


def test_the_aws_provider_hands_back_a_pool_driver() -> None:
    assert AwsProvider().pool_driver() is not None
