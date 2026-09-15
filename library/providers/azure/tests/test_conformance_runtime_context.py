from collections.abc import Generator

import pytest
from azure_conformance import install, runtime_entry
from tests.application.ports.conformance.providers import ProviderUnderTest
from tests.application.ports.conformance.test_runtime_context import *  # noqa: F403

from library_provider_azure.settings import RESOURCE_GROUP


@pytest.fixture(autouse=True)
def _resource_group(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv(RESOURCE_GROUP, "acme-production")


@pytest.fixture
def provider_under_test() -> Generator[ProviderUnderTest]:
    yield from install(runtime_entry())
