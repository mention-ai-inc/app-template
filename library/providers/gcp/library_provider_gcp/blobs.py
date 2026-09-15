import os
from datetime import datetime
from typing import Literal

import httpx

from library.domain.value_objects.common import PresignedURL, Service
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.persistence.storage import SERVICE_BUCKETS, BucketName, ObjectNotFoundError
from library_provider_gcp.cloud.project import get_project_id
from library_provider_gcp.cloud.storage import Storage


class ServiceBucket:
    def __init__(
        self, *, service: Service, bucket: BucketName, token: str | None = None, feature_environment: str | None = None
    ) -> None:
        if bucket not in SERVICE_BUCKETS.get(service, []):
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"This service ({service.value}) does not have a bucket called {bucket.value}",
            )

        self._storage = Storage(token=token)
        self._bucket = (
            f"{get_project_id()}--{feature_environment or os.getenv('FEATURE_ENVIRONMENT', '')}{service}-{bucket.value}"
        )

    @staticmethod
    def org_prefix(organization_id: OrganizationID) -> str:
        return f"orgs/{organization_id}/"

    def get_path_to_blob(self, *, organization_id: OrganizationID, document_id: str, field_id: str) -> str:
        return f"{self.org_prefix(organization_id)}blobs/{document_id}/{field_id}.blob"

    def get_legacy_path_to_blob(self, *, document_id: str, field_id: str) -> str:
        return f"blobs/{document_id}/{field_id}.blob"

    async def delete_all_under(self, *, prefix: str) -> None:
        filepaths = await self.list(prefix=prefix)
        for filepath in filepaths:
            await self.delete(filepath=filepath)

    async def exists(self, *, filepath: str) -> bool:
        return await self._storage.exists(filepath=filepath, bucket=self._bucket)

    async def insert(self, *, filepath: str, content: bytes) -> None:
        await self._storage.insert(filepath=filepath, content=content, bucket=self._bucket)

    async def get(self, *, filepath: str) -> bytes:
        try:
            return await self._storage.get(filepath=filepath, bucket=self._bucket)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise ObjectNotFoundError(filepath)
            else:
                raise

    async def get_saved_at(self, *, filepath: str) -> datetime:
        try:
            return await self._storage.get_saved_at(filepath=filepath, bucket=self._bucket)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise ObjectNotFoundError(filepath)
            else:
                raise

    async def delete(self, *, filepath: str) -> None:
        try:
            await self._storage.delete(filepath=filepath, bucket=self._bucket)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise ObjectNotFoundError(filepath)
            else:
                raise

    async def list(self, *, prefix: str = "") -> list[str]:
        storage_objects = await self._storage.list_files(prefix=prefix, bucket=self._bucket)
        return [storage_object.name for storage_object in storage_objects]

    async def get_presigned_url(
        self, *, filepath: str, expiration: int, content_type: str, method: Literal["GET", "PUT"]
    ) -> PresignedURL:
        for _ in range(2):
            try:
                return PresignedURL(
                    await self._storage.get_presigned_url(
                        filepath=filepath,
                        bucket=self._bucket,
                        method=method,
                        expiration=expiration,
                        content_type=content_type,
                    )
                )
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 404:
                    await self._storage.insert(filepath=filepath, content=b"", bucket=self._bucket)
                else:
                    raise

        raise ObjectNotFoundError(filepath)
