import os
from datetime import UTC, datetime
from typing import Any, Literal, cast

from botocore.exceptions import ClientError

from library.domain.value_objects.common import PresignedURL, Service
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.persistence.storage import SERVICE_BUCKETS, BucketName, ObjectNotFoundError
from library_provider_aws.clients import client, error_code, get_account_id

MISSING_OBJECT_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
LIST_PAGE_SIZE = 1000
SAVED_AT_METADATA_KEY = "saved-at"


class S3Bucket:
    def __init__(self, *, service: Service, bucket: BucketName, feature_environment: str | None = None) -> None:
        if bucket not in SERVICE_BUCKETS.get(service, []):
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"This service ({service.value}) does not have a bucket called {bucket.value}",
            )

        environment = feature_environment if feature_environment is not None else os.getenv("FEATURE_ENVIRONMENT", "")
        self._bucket = f"{get_account_id()}--{environment}{service.value}-{bucket.value}"

    @property
    def bucket(self) -> str:
        return self._bucket

    @staticmethod
    def org_prefix(organization_id: OrganizationID) -> str:
        return f"orgs/{organization_id}/"

    def get_path_to_blob(self, *, organization_id: OrganizationID, document_id: str, field_id: str) -> str:
        return f"{self.org_prefix(organization_id)}blobs/{document_id}/{field_id}.blob"

    def get_legacy_path_to_blob(self, *, document_id: str, field_id: str) -> str:
        return f"blobs/{document_id}/{field_id}.blob"

    async def exists(self, *, filepath: str) -> bool:
        try:
            async with client("s3") as s3:
                await s3.head_object(Bucket=self._bucket, Key=filepath)
        except ClientError as error:
            if self.__is_missing(error):
                return False
            raise
        return True

    async def insert(self, *, filepath: str, content: bytes) -> None:
        async with client("s3") as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=filepath,
                Body=content,
                Metadata={SAVED_AT_METADATA_KEY: datetime.now(UTC).isoformat()},
            )

    async def get(self, *, filepath: str) -> bytes:
        try:
            async with client("s3") as s3:
                response = await s3.get_object(Bucket=self._bucket, Key=filepath)
                return await response["Body"].read()
        except ClientError as error:
            if self.__is_missing(error):
                raise ObjectNotFoundError(filepath) from error
            raise

    async def get_saved_at(self, *, filepath: str) -> datetime:
        try:
            async with client("s3") as s3:
                response = await s3.head_object(Bucket=self._bucket, Key=filepath)
        except ClientError as error:
            if self.__is_missing(error):
                raise ObjectNotFoundError(filepath) from error
            raise

        recorded = response.get("Metadata", {}).get(SAVED_AT_METADATA_KEY)
        if recorded is None:
            return response["LastModified"]
        return datetime.fromisoformat(str(recorded))

    async def delete(self, *, filepath: str) -> None:
        if not await self.exists(filepath=filepath):
            raise ObjectNotFoundError(filepath)

        async with client("s3") as s3:
            await s3.delete_object(Bucket=self._bucket, Key=filepath)

    async def delete_all_under(self, *, prefix: str) -> None:
        for filepath in await self.list(prefix=prefix):
            await self.delete(filepath=filepath)

    async def list(self, *, prefix: str = "") -> list[str]:
        filepaths: list[str] = []
        continuation_token: str | None = None

        async with client("s3") as s3:
            while True:
                request: dict[str, Any] = {
                    "Bucket": self._bucket,
                    "Prefix": prefix,
                    "MaxKeys": LIST_PAGE_SIZE,
                }
                if continuation_token is not None:
                    request["ContinuationToken"] = continuation_token
                response = await s3.list_objects_v2(**request)
                filepaths.extend(str(stored["Key"]) for stored in response.get("Contents", []))
                continuation_token = response.get("NextContinuationToken")
                if continuation_token is None:
                    return sorted(filepaths)

    async def get_presigned_url(
        self, *, filepath: str, expiration: int, content_type: str, method: Literal["GET", "PUT"]
    ) -> PresignedURL:
        if not await self.exists(filepath=filepath):
            await self.insert(filepath=filepath, content=b"")

        parameters: dict[str, Any] = {"Bucket": self._bucket, "Key": filepath}
        if method == "PUT":
            parameters["ContentType"] = content_type

        async with client("s3", for_presigning=True) as s3:
            signed = cast(
                str,
                await s3.generate_presigned_url(
                    ClientMethod="put_object" if method == "PUT" else "get_object",
                    Params=parameters,
                    ExpiresIn=expiration,
                ),
            )

        return PresignedURL(signed)

    def __is_missing(self, error: ClientError, /) -> bool:
        return error_code(error) in MISSING_OBJECT_CODES
