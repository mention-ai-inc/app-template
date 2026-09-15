from collections.abc import Generator

import pytest
from azure_conformance import estate_entry, install
from tests.application.ports.conformance.providers import ProviderUnderTest


@pytest.fixture
def provider_under_test() -> Generator[ProviderUnderTest]:
    yield from install(estate_entry())
