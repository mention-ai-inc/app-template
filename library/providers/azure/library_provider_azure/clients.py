import os

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.keys.aio import KeyClient
from azure.keyvault.secrets.aio import SecretClient
from azure.servicebus.aio import ServiceBusClient
from azure.storage.blob.aio import BlobServiceClient

from library_provider_azure.settings import (
    BLOB_ACCOUNT_KEY,
    BLOB_ACCOUNT_URL,
    COSMOS_DATABASE,
    COSMOS_ENDPOINT,
    COSMOS_KEY,
    KEY_VAULT_URI,
    SERVICE_BUS_NAMESPACE,
    required,
    tls_verification_enabled,
)


class AzureClients:
    _credential: DefaultAzureCredential | None = None
    _cosmos: CosmosClient | None = None
    _containers: dict[str, ContainerProxy] = {}
    _service_bus: ServiceBusClient | None = None
    _blobs: BlobServiceClient | None = None
    _secrets: SecretClient | None = None
    _keys: KeyClient | None = None

    @classmethod
    def credential(cls) -> DefaultAzureCredential:
        if cls._credential is None:
            cls._credential = DefaultAzureCredential()
        return cls._credential

    @classmethod
    def cosmos(cls) -> CosmosClient:
        if cls._cosmos is None:
            key = os.getenv(COSMOS_KEY)
            cls._cosmos = CosmosClient(
                url=required(COSMOS_ENDPOINT),
                credential=key if key else cls.credential(),
                connection_verify=tls_verification_enabled(),
            )
        return cls._cosmos

    @classmethod
    def container(cls, container_name: str, /) -> ContainerProxy:
        if container_name not in cls._containers:
            database = cls.cosmos().get_database_client(required(COSMOS_DATABASE))
            cls._containers[container_name] = database.get_container_client(container_name)
        return cls._containers[container_name]

    @classmethod
    def service_bus(cls) -> ServiceBusClient:
        if cls._service_bus is None:
            cls._service_bus = ServiceBusClient(
                fully_qualified_namespace=required(SERVICE_BUS_NAMESPACE), credential=cls.credential()
            )
        return cls._service_bus

    @classmethod
    def blobs(cls) -> BlobServiceClient:
        if cls._blobs is None:
            key = os.getenv(BLOB_ACCOUNT_KEY)
            cls._blobs = BlobServiceClient(
                account_url=required(BLOB_ACCOUNT_URL), credential=key if key else cls.credential()
            )
        return cls._blobs

    @classmethod
    def secrets(cls) -> SecretClient:
        if cls._secrets is None:
            cls._secrets = SecretClient(vault_url=required(KEY_VAULT_URI), credential=cls.credential())
        return cls._secrets

    @classmethod
    def keys(cls) -> KeyClient:
        if cls._keys is None:
            cls._keys = KeyClient(vault_url=required(KEY_VAULT_URI), credential=cls.credential())
        return cls._keys

    @classmethod
    def reset(cls) -> None:
        cls._credential = None
        cls._cosmos = None
        cls._containers = {}
        cls._service_bus = None
        cls._blobs = None
        cls._secrets = None
        cls._keys = None
