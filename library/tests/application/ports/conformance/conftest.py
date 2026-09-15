from collections.abc import Callable, Generator

import pytest

from library.application.ports.blobs import IBlobStore
from library.application.ports.eventbus import IEventBus
from library.application.ports.identity import IIdentity
from library.application.ports.jobs import IJobRunner
from library.application.ports.logs import ILogReader
from library.application.ports.operators import IOperatorAuth
from library.application.ports.provider import ICloudProvider
from library.application.ports.runtime import IRuntimeContext
from library.application.ports.secrets import ISecretStore
from library.application.ports.taskqueue import ITaskQueue
from library.providers.registry import get_cloud_provider, reset_cloud_provider, set_cloud_provider
from tests.application.ports.conformance.providers import (
    CONFORMANCE_BUCKET,
    CONFORMANCE_SERVICE,
    PROVIDERS_UNDER_TEST,
    ProviderUnderTest,
    RecordedMessage,
    RecordedTask,
)
from tests.application.ports.conformance.stores import MainStore, SimpleStore
from tests.infrastructure.persistence.mocks import MainEntity, MockPartitionKey, SimpleEntity


@pytest.fixture(params=PROVIDERS_UNDER_TEST, ids=[entry.name for entry in PROVIDERS_UNDER_TEST])
def provider_under_test(request: pytest.FixtureRequest) -> Generator[ProviderUnderTest]:
    entry: ProviderUnderTest = request.param

    if entry.skip_reason is not None:
        pytest.skip(f"{entry.name}: {entry.skip_reason}")

    set_cloud_provider(entry.factory())
    if entry.reset is not None:
        entry.reset()

    yield entry

    if entry.reset is not None:
        entry.reset()
    reset_cloud_provider()


@pytest.fixture
def provider(provider_under_test: ProviderUnderTest) -> ICloudProvider:  # noqa: ARG001
    return get_cloud_provider()


@pytest.fixture
def simple_store(provider: ICloudProvider) -> SimpleStore:
    return provider.document_store(
        collection="simple",
        model=SimpleEntity,
        partition_key_type=MockPartitionKey,
        service=CONFORMANCE_SERVICE,
    )


@pytest.fixture
def main_store(provider: ICloudProvider) -> MainStore:
    return provider.document_store(
        collection="main",
        model=MainEntity,
        partition_key_type=MockPartitionKey,
        service=CONFORMANCE_SERVICE,
    )


@pytest.fixture
def event_bus(provider: ICloudProvider) -> IEventBus:
    return provider.event_bus()


@pytest.fixture
def task_queue(provider: ICloudProvider) -> ITaskQueue:
    return provider.task_queue()


@pytest.fixture
def blob_store(provider: ICloudProvider) -> IBlobStore:
    return provider.blob_store(service=CONFORMANCE_SERVICE, bucket=CONFORMANCE_BUCKET)


@pytest.fixture
def secret_store(provider: ICloudProvider) -> ISecretStore:
    return provider.secret_store()


@pytest.fixture
def identity(provider: ICloudProvider) -> IIdentity:
    return provider.identity()


@pytest.fixture
def runtime_context(provider: ICloudProvider) -> IRuntimeContext:
    return provider.runtime_context()


@pytest.fixture
def read_recorded_messages(provider_under_test: ProviderUnderTest) -> Callable[[], list[RecordedMessage]]:
    if provider_under_test.recorded_messages is None:
        pytest.skip(f"{provider_under_test.name} cannot inspect published messages")
    return provider_under_test.recorded_messages


@pytest.fixture
def read_recorded_tasks(provider_under_test: ProviderUnderTest) -> Callable[[], list[RecordedTask]]:
    if provider_under_test.recorded_tasks is None:
        pytest.skip(f"{provider_under_test.name} cannot inspect enqueued tasks")
    return provider_under_test.recorded_tasks


@pytest.fixture
def job_runner(provider: ICloudProvider) -> IJobRunner:
    return provider.job_runner()


@pytest.fixture
def log_reader(provider: ICloudProvider) -> ILogReader:
    return provider.log_reader()


@pytest.fixture
def operator_auth(provider: ICloudProvider) -> IOperatorAuth:
    return provider.operator_auth()


@pytest.fixture
def conformance_job(provider_under_test: ProviderUnderTest) -> str:
    if provider_under_test.install_conformance_job is None:
        pytest.skip(f"{provider_under_test.name} has no job it can run under test")
    return provider_under_test.install_conformance_job()


@pytest.fixture
def operator_headers(provider_under_test: ProviderUnderTest) -> dict[str, str]:
    if provider_under_test.operator_headers is None:
        pytest.skip(f"{provider_under_test.name} cannot mint operator headers")
    return provider_under_test.operator_headers()
