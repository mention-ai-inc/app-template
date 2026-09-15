import asyncio
import os
from collections.abc import Generator

import pytest
from azure.core.exceptions import ResourceNotFoundError
from tests.application.ports.conformance.providers import CONFORMANCE_BUCKET, CONFORMANCE_SERVICE, ProviderUnderTest

from library.infrastructure.persistence.storage import BucketName
from library.providers.registry import reset_cloud_provider, set_cloud_provider
from library_provider_azure.clients import AzureClients
from library_provider_azure.documents import PARTITION_KEY_FIELD
from library_provider_azure.provider import PROVIDER as AZURE_PROVIDER
from library_provider_azure.settings import (
    BLOB_ACCOUNT_URL,
    COSMOS_DATABASE,
    COSMOS_ENDPOINT,
    KEY_VAULT_URI,
    SERVICE_BUS_NAMESPACE,
)

COSMOS_VARIABLES = (COSMOS_ENDPOINT, COSMOS_DATABASE)
BLOB_VARIABLES = (BLOB_ACCOUNT_URL,)
SERVICE_BUS_VARIABLES = (SERVICE_BUS_NAMESPACE,)
KEY_VAULT_VARIABLES = (KEY_VAULT_URI,)


def install(entry: ProviderUnderTest, /) -> Generator[ProviderUnderTest]:
    if entry.skip_reason is not None:
        pytest.skip(f"{entry.name}: {entry.skip_reason}")

    set_cloud_provider(entry.factory())
    if entry.reset is not None:
        entry.reset()

    yield entry

    if entry.reset is not None:
        entry.reset()
    reset_cloud_provider()


def runtime_entry() -> ProviderUnderTest:
    return ProviderUnderTest(name="azure", factory=lambda: AZURE_PROVIDER, reset=reset_nothing)


def skip_reason_for(*variables: str) -> str | None:
    absent = [variable for variable in variables if not os.getenv(variable)]
    if len(absent) == 0:
        return None
    return f"no Azure estate reachable: {', '.join(absent)} not set"


def cosmos_entry() -> ProviderUnderTest:
    return ProviderUnderTest(
        name="azure",
        factory=lambda: AZURE_PROVIDER,
        reset=reset_cosmos,
        skip_reason=skip_reason_for(*COSMOS_VARIABLES),
    )


def blob_entry() -> ProviderUnderTest:
    return ProviderUnderTest(
        name="azure",
        factory=lambda: AZURE_PROVIDER,
        reset=reset_blobs,
        skip_reason=skip_reason_for(*BLOB_VARIABLES),
        supports_presigned_urls=user_delegation_signing_available(),
        presigned_urls_create_missing_objects=user_delegation_signing_available(),
    )


def service_bus_entry() -> ProviderUnderTest:
    return ProviderUnderTest(
        name="azure",
        factory=lambda: AZURE_PROVIDER,
        reset=reset_nothing,
        skip_reason=skip_reason_for(*SERVICE_BUS_VARIABLES),
    )


def key_vault_entry() -> ProviderUnderTest:
    return ProviderUnderTest(
        name="azure",
        factory=lambda: AZURE_PROVIDER,
        reset=reset_nothing,
        skip_reason=skip_reason_for(*KEY_VAULT_VARIABLES),
    )


def estate_entry() -> ProviderUnderTest:
    return ProviderUnderTest(
        name="azure",
        factory=lambda: AZURE_PROVIDER,
        reset=reset_nothing,
        skip_reason=skip_reason_for(*COSMOS_VARIABLES, *BLOB_VARIABLES, *SERVICE_BUS_VARIABLES, *KEY_VAULT_VARIABLES),
    )


def user_delegation_signing_available() -> bool:
    return not os.getenv("BLOB_ACCOUNT_KEY")


def reset_nothing() -> None:
    AzureClients.reset()


def reset_cosmos() -> None:
    AzureClients.reset()
    asyncio.run(_empty_container())
    AzureClients.reset()


def reset_blobs() -> None:
    AzureClients.reset()
    asyncio.run(_empty_blob_container())
    AzureClients.reset()


async def _empty_container() -> None:
    container = AzureClients.container(CONFORMANCE_SERVICE.value)
    items = [item async for item in container.query_items(query=f"SELECT c.id, c.{PARTITION_KEY_FIELD} FROM c")]
    for item in items:
        await container.delete_item(item=item["id"], partition_key=item[PARTITION_KEY_FIELD])
    await AzureClients.cosmos().close()


async def _empty_blob_container() -> None:
    store = AZURE_PROVIDER.blob_store(service=CONFORMANCE_SERVICE, bucket=BucketName(CONFORMANCE_BUCKET))
    try:
        for filepath in await store.list():
            await store.delete(filepath=filepath)
    except ResourceNotFoundError:
        pass
    await AzureClients.blobs().close()
