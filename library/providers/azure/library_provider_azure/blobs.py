from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobClient, ContainerClient

from library.domain.value_objects.common import PresignedURL, Service
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.persistence.storage import SERVICE_BUCKETS, BucketName, ObjectNotFoundError
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import feature_environment

DELEGATION_KEY_LEEWAY_SECONDS = 300
SAVED_AT_METADATA = "saved_at"


class BlobContainer:
    def __init__(
        self, *, service: Service, bucket: BucketName, feature_environment_override: str | None = None
    ) -> None:
        if bucket not in SERVICE_BUCKETS.get(service, []):
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"This service ({service.value}) does not have a bucket called {bucket.value}",
            )

        environment = feature_environment_override or feature_environment()
        self._container_name = f"{environment}{service}-{bucket.value}"

    @staticmethod
    def org_prefix(organization_id: OrganizationID) -> str:
        return f"orgs/{organization_id}/"

    def get_path_to_blob(self, *, organization_id: OrganizationID, document_id: str, field_id: str) -> str:
        return f"{self.org_prefix(organization_id)}blobs/{document_id}/{field_id}.blob"

    def get_legacy_path_to_blob(self, *, document_id: str, field_id: str) -> str:
        return f"blobs/{document_id}/{field_id}.blob"

    async def exists(self, *, filepath: str) -> bool:
        return await self.__blob(filepath).exists()

    async def insert(self, *, filepath: str, content: bytes) -> None:
        await self.__blob(filepath).upload_blob(
            content, overwrite=True, metadata={SAVED_AT_METADATA: datetime.now(UTC).isoformat()}
        )

    async def get(self, *, filepath: str) -> bytes:
        try:
            stream = await self.__blob(filepath).download_blob()
            return await stream.readall()
        except ResourceNotFoundError:
            raise ObjectNotFoundError(filepath)

    async def get_saved_at(self, *, filepath: str) -> datetime:
        try:
            properties = await self.__blob(filepath).get_blob_properties()
        except ResourceNotFoundError:
            raise ObjectNotFoundError(filepath)

        recorded = (properties.metadata or {}).get(SAVED_AT_METADATA)
        if recorded is not None:
            return datetime.fromisoformat(recorded)

        return properties.last_modified

    async def delete(self, *, filepath: str) -> None:
        try:
            await self.__blob(filepath).delete_blob()
        except ResourceNotFoundError:
            raise ObjectNotFoundError(filepath)

    async def delete_all_under(self, *, prefix: str) -> None:
        for filepath in await self.list(prefix=prefix):
            await self.delete(filepath=filepath)

    async def list(self, *, prefix: str = "") -> list[str]:
        names: list[str] = []
        async for name in self.__container().list_blob_names(name_starts_with=prefix):
            names.append(name)
        return sorted(names)

    async def get_presigned_url(
        self, *, filepath: str, expiration: int, content_type: str, method: Literal["GET", "PUT"]
    ) -> PresignedURL:
        if not await self.exists(filepath=filepath):
            await self.insert(filepath=filepath, content=b"")

        blob = self.__blob(filepath)
        starts_at = datetime.now(UTC) - timedelta(seconds=DELEGATION_KEY_LEEWAY_SECONDS)
        expires_at = datetime.now(UTC) + timedelta(seconds=expiration)
        delegation_key = await AzureClients.blobs().get_user_delegation_key(
            key_start_time=starts_at, key_expiry_time=expires_at
        )

        signature = generate_blob_sas(
            account_name=self.__account_name(),
            container_name=self._container_name,
            blob_name=filepath,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True)
            if method == "GET"
            else BlobSasPermissions(write=True, create=True),
            start=starts_at,
            expiry=expires_at,
            content_type=content_type,
        )

        return PresignedURL(f"{blob.url}?{signature}")

    def __container(self) -> ContainerClient:
        return AzureClients.blobs().get_container_client(self._container_name)

    def __blob(self, filepath: str, /) -> BlobClient:
        return self.__container().get_blob_client(filepath)

    def __account_name(self) -> str:
        host = urlparse(AzureClients.blobs().url).hostname or ""
        return host.split(".")[0]
