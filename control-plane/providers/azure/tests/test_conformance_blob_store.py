from collections.abc import Generator

import pytest
from azure_conformance import blob_entry, install
from tests.application.ports.conformance.providers import ProviderUnderTest
from tests.application.ports.conformance.test_blob_store import *  # noqa: F403


@pytest.fixture
def provider_under_test() -> Generator[ProviderUnderTest]:
    yield from install(blob_entry())
