from dataclasses import dataclass, field

import pytest
from azure.core.exceptions import ResourceNotFoundError
from pytest_mock import MockerFixture

from library.infrastructure.errors import InfrastructureError
from library_provider_azure.secrets import KeyVaultSecretStore, to_key_vault_name


@dataclass
class FakeSecret:
    value: str | None


@dataclass
class FakeSecretClient:
    secrets: dict[str, str]
    requested: list[tuple[str, str | None]] = field(default_factory=list[tuple[str, str | None]])

    async def get_secret(self, name: str, version: str | None = None) -> FakeSecret:
        self.requested.append((name, version))
        if name not in self.secrets:
            raise ResourceNotFoundError(message=f"no secret {name}")
        return FakeSecret(value=self.secrets[name])


@pytest.fixture
def secret_client(mocker: MockerFixture) -> FakeSecretClient:
    client = FakeSecretClient(secrets={"CLERK-SECRET-KEY": "sk_test"})
    mocker.patch("library_provider_azure.secrets.AzureClients.secrets", return_value=client)
    return client


def test_an_underscored_secret_id_becomes_a_key_vault_name() -> None:
    assert to_key_vault_name("CLERK_SECRET_KEY") == "CLERK-SECRET-KEY"


async def test_the_latest_version_is_asked_for_by_omitting_the_version(secret_client: FakeSecretClient) -> None:
    assert await KeyVaultSecretStore().access_secret_version(secret_id="CLERK_SECRET_KEY") == "sk_test"
    assert secret_client.requested == [("CLERK-SECRET-KEY", None)]


async def test_an_explicit_version_is_passed_through(secret_client: FakeSecretClient) -> None:
    await KeyVaultSecretStore().access_secret_version(secret_id="CLERK_SECRET_KEY", version_id="abc123")

    assert secret_client.requested == [("CLERK-SECRET-KEY", "abc123")]


async def test_a_missing_secret_is_a_cloud_error(secret_client: FakeSecretClient) -> None:  # noqa: ARG001
    with pytest.raises(InfrastructureError, match="Error accessing secret"):
        await KeyVaultSecretStore().access_secret_version(secret_id="ABSENT")
