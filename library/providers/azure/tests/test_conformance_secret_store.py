from collections.abc import Generator

import pytest
from azure_conformance import install, key_vault_entry
from tests.application.ports.conformance.providers import ProviderUnderTest
from tests.application.ports.conformance.test_secret_store import *  # noqa: F403


@pytest.fixture
def provider_under_test() -> Generator[ProviderUnderTest]:
    yield from install(key_vault_entry())
