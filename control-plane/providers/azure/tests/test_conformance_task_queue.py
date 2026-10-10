from collections.abc import Generator

import pytest
from azure_conformance import install, service_bus_entry
from tests.application.ports.conformance.providers import ProviderUnderTest
from tests.application.ports.conformance.test_task_queue import *  # noqa: F403


@pytest.fixture
def provider_under_test() -> Generator[ProviderUnderTest]:
    yield from install(service_bus_entry())
