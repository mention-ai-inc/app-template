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
from library_provider_aws.blobs import S3Bucket
from library_provider_aws.changefeed import DynamoDbStreamRecord
from library_provider_aws.dynamodb import DynamoDbDocumentStore
from library_provider_aws.events import SnsMessageParser
from library_provider_aws.identity import AwsRuntimeContext, KmsIdentity
from library_provider_aws.jobs import EcsJobRunner
from library_provider_aws.logs import CloudWatchLogReader
from library_provider_aws.messaging import SnsEventBus, SqsTaskQueue
from library_provider_aws.operators import AlbOperatorAuth
from library_provider_aws.pools import SqsPoolDriver
from library_provider_aws.secrets import SecretsManager
from library_provider_aws.transactions import AwsTransaction
from library_provider_aws.unit_of_work import aws_unit_of_work, get_current_aws_transaction


class AwsProvider:
    def __init__(self) -> None:
        self._job_runner = EcsJobRunner()
        self._log_reader = CloudWatchLogReader(job_runner=self._job_runner)
        self._operator_auth = AlbOperatorAuth()

    @property
    def name(self) -> str:
        return "aws"

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
        return DynamoDbDocumentStore(
            collection=collection,
            model=model,
            partition_key_type=partition_key_type,
            service=service,
            feature_environment=feature_environment,
        )

    def unit_of_work(self) -> AbstractAsyncContextManager[None]:
        return aws_unit_of_work()

    def current_transaction(self) -> AwsTransaction:
        return get_current_aws_transaction()

    def change_feed[DataT: BaseModel](self, data_model: type[DataT], /) -> DynamoDbStreamRecord[DataT]:
        return DynamoDbStreamRecord(data_model)

    def event_bus(self) -> SnsEventBus:
        return SnsEventBus()

    def message_parser[DataT: EventPayload](
        self, *, data_models: list[type[DataT]], cache: IAsyncCache, deduplication_ttl_ms: int | None = None
    ) -> SnsMessageParser[DataT]:
        return SnsMessageParser(data_models=data_models, cache=cache, deduplication_ttl_ms=deduplication_ttl_ms)

    def task_queue(self) -> SqsTaskQueue:
        return SqsTaskQueue()

    def blob_store(self, *, service: Service, bucket: str, feature_environment: str | None = None) -> S3Bucket:
        return S3Bucket(service=service, bucket=BucketName(bucket), feature_environment=feature_environment)

    def secret_store(self) -> SecretsManager:
        return SecretsManager()

    def identity(self) -> KmsIdentity:
        return KmsIdentity()

    def runtime_context(self) -> AwsRuntimeContext:
        return AwsRuntimeContext()

    def job_runner(self) -> EcsJobRunner:
        return self._job_runner

    def log_reader(self) -> CloudWatchLogReader:
        return self._log_reader

    def operator_auth(self) -> AlbOperatorAuth:
        return self._operator_auth

    def pool_driver(self) -> SqsPoolDriver:
        return SqsPoolDriver()


PROVIDER = AwsProvider()
