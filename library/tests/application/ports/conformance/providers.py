from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from library.application.ports.provider import ICloudProvider
from library.domain.value_objects.common import Service
from library.infrastructure.persistence.storage import BucketName
from library.providers.local.database import LocalDatabase
from library.providers.local.messaging import LocalEventBus
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER

CONFORMANCE_SERVICE = Service.NOTES
CONFORMANCE_BUCKET = BucketName.CACHE.value


@dataclass(frozen=True)
class RecordedMessage:
    topic_name: str
    data: str
    attributes: dict[str, str]
    message_id: str


@dataclass(frozen=True)
class RecordedTask:
    service: str
    task: str
    body: dict[str, Any]
    params: dict[str, str] | None
    headers: dict[str, str] | None
    scheduled_time: datetime | None


@dataclass(frozen=True)
class ProviderUnderTest:
    name: str
    factory: Callable[[], ICloudProvider]
    reset: Callable[[], None] | None = None
    skip_reason: str | None = None
    supports_presigned_urls: bool = True
    presigned_urls_create_missing_objects: bool = True
    recorded_messages: Callable[[], list[RecordedMessage]] | None = None
    recorded_tasks: Callable[[], list[RecordedTask]] | None = None


def reset_local() -> None:
    LocalDatabase.clear()
    LocalEventBus.clear()
    LOCAL_PROVIDER.task_queue().enqueued.clear()
    LOCAL_PROVIDER.blob_store(service=CONFORMANCE_SERVICE, bucket=CONFORMANCE_BUCKET).blobs.clear()


def local_recorded_messages() -> list[RecordedMessage]:
    return [
        RecordedMessage(
            topic_name=published.topic_name,
            data=published.data,
            attributes=published.attributes,
            message_id=published.message_id,
        )
        for published in LocalEventBus.published
    ]


def local_recorded_tasks() -> list[RecordedTask]:
    return [
        RecordedTask(
            service=enqueued.service,
            task=enqueued.task,
            body=enqueued.body,
            params=enqueued.params,
            headers=enqueued.headers,
            scheduled_time=enqueued.scheduled_time,
        )
        for enqueued in LOCAL_PROVIDER.task_queue().enqueued
    ]


LOCAL = ProviderUnderTest(
    name="local",
    factory=lambda: LOCAL_PROVIDER,
    reset=reset_local,
    recorded_messages=local_recorded_messages,
    recorded_tasks=local_recorded_tasks,
)

PROVIDERS_UNDER_TEST: list[ProviderUnderTest] = [LOCAL]
