import os
from collections.abc import Generator

import pytest
from aws_under_test import ACCOUNT_ID, AWS, TABLE_NAME, AwsEstate, set_estate
from library_provider_aws.clients import reset_account_id
from moto.server import ThreadedMotoServer  # pyright: ignore[reportMissingImports]
from tests.application.ports.conformance.conftest import (
    blob_store,  # noqa: F401
    event_bus,  # noqa: F401
    identity,  # noqa: F401
    main_store,  # noqa: F401
    provider,  # noqa: F401
    read_recorded_messages,  # noqa: F401
    read_recorded_tasks,  # noqa: F401
    runtime_context,  # noqa: F401
    secret_store,  # noqa: F401
    simple_store,  # noqa: F401
    task_queue,  # noqa: F401
)
from tests.application.ports.conformance.providers import ProviderUnderTest

from library.providers.registry import reset_cloud_provider, set_cloud_provider

__all__ = [
    "REGION",
    "blob_store",
    "event_bus",
    "identity",
    "main_store",
    "moto_endpoint",
    "provider",
    "provider_under_test",
    "read_recorded_messages",
    "read_recorded_tasks",
    "runtime_context",
    "secret_store",
    "simple_store",
    "task_queue",
]

REGION = "us-east-1"


@pytest.fixture(scope="session", autouse=True)
def moto_endpoint() -> Generator[str]:
    server = ThreadedMotoServer(port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    endpoint_url = f"http://{host}:{port}"

    os.environ.update(
        AWS_ACCESS_KEY_ID="conformance",
        AWS_SECRET_ACCESS_KEY="conformance",
        AWS_SESSION_TOKEN="conformance",
        AWS_DEFAULT_REGION=REGION,
        AWS_REGION=REGION,
        AWS_ENDPOINT_URL=endpoint_url,
        AWS_ACCOUNT_ID=ACCOUNT_ID,
        DYNAMODB_TABLE_NAME=TABLE_NAME,
        FEATURE_ENVIRONMENT="",
    )
    reset_account_id()

    estate = AwsEstate(endpoint_url=endpoint_url, region=REGION)
    estate.create()
    set_estate(estate)

    yield endpoint_url

    server.stop()


@pytest.fixture
def provider_under_test(moto_endpoint: str) -> Generator[ProviderUnderTest]:  # noqa: ARG001
    set_cloud_provider(AWS.factory())
    if AWS.reset is not None:
        AWS.reset()

    yield AWS

    if AWS.reset is not None:
        AWS.reset()
    reset_cloud_provider()
