import asyncio
import base64
import hashlib
import logging
import os
import random
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote, quote_plus

from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from library.logs import SIMPLE_LOGGER_NAME
from library_provider_gcp.cloud.base import AuthenticatedClient, raise_for_status
from library_provider_gcp.cloud.iam import IAM
from library_provider_gcp.cloud.project import get_project_id

logger = logging.getLogger(SIMPLE_LOGGER_NAME)

INSERT_RETRY_ATTEMPTS = 4
INSERT_RETRY_BASE_DELAY_SECONDS = 1.0
_RATE_LIMITED_STATUS_CODE = 429


class StorageObject(BaseModel):
    bucket: str
    name: str
    updated: datetime
    media_link: str = Field(..., validation_alias="mediaLink")
    md5_hash: str = Field(..., validation_alias="md5Hash")
    size: int = Field(..., ge=0)
    time_created: datetime = Field(..., validation_alias="timeCreated")


class Storage:
    BASE_URL = "https://storage.googleapis.com/storage/v1"
    BASE_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1"

    def __init__(self, *, token: str | None = None) -> None:
        self.token = token
        self._client: AuthenticatedClient | None = None
        self._upload_client: AuthenticatedClient | None = AuthenticatedClient(
            base_url=Storage.BASE_UPLOAD_URL, token=token
        )
        self.iam_client = IAM()

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=Storage.BASE_URL, token=self.token)
        return self._client

    @property
    def upload_client(self) -> AuthenticatedClient:
        if self._upload_client is None:
            self._upload_client = AuthenticatedClient(base_url=Storage.BASE_UPLOAD_URL, token=self.token)
        return self._upload_client

    async def insert(self, *, filepath: str, content: bytes, bucket: str) -> None:
        attempt = 0
        while True:
            response = await self.upload_client.post(
                f"/b/{bucket}/o", params={"uploadType": "media", "name": filepath}, content=content
            )
            attempt += 1
            if response.status_code == _RATE_LIMITED_STATUS_CODE and attempt < INSERT_RETRY_ATTEMPTS:
                delay = INSERT_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
                logger.warning(
                    f"Rate limited writing gs://{bucket}/{filepath} "
                    f"(attempt {attempt}/{INSERT_RETRY_ATTEMPTS}); retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            raise_for_status(response)
            return

    async def list_files(self, *, prefix: str = "", bucket: str) -> list[StorageObject]:
        storage_objects: list[StorageObject] = []
        response = await self.client.get(f"/b/{bucket}/o", params={"prefix": prefix})
        raise_for_status(response)

        for item in response.json().get("items", []):
            storage_object = StorageObject.model_validate(item)
            storage_objects.append(storage_object)

        return storage_objects

    async def get(self, *, filepath: str, bucket: str) -> bytes:
        response = await self.client.get(f"/b/{bucket}/o/{quote_plus(filepath)}", params={"alt": "media"})
        raise_for_status(response)
        return response.content

    async def get_saved_at(self, *, filepath: str, bucket: str) -> datetime:
        response = await self.client.get(f"/b/{bucket}/o/{quote_plus(filepath)}", params={"fields": "updated"})
        raise_for_status(response)
        return datetime.fromisoformat(response.json()["updated"]).replace(tzinfo=UTC)

    async def delete(self, *, filepath: str, bucket: str) -> None:
        response = await self.client.delete(f"/b/{bucket}/o/{quote_plus(filepath)}")
        raise_for_status(response)

    async def exists(self, *, filepath: str, bucket: str) -> bool:
        try:
            response = await self.client.get(f"/b/{bucket}/o/{quote_plus(filepath)}", params={"fields": "name"})
            response.raise_for_status()
            return True
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    async def get_presigned_url(
        self, *, filepath: str, bucket: str, method: Literal["GET", "PUT"], expiration: int, content_type: str
    ) -> str:
        canonical_uri = f"/{quote(filepath, safe='/~')}"
        now = datetime.now(UTC)
        request_timestamp = now.strftime("%Y%m%dT%H%M%SZ")
        datestamp = now.strftime("%Y%m%d")

        service_account_email = f"{os.getenv('FEATURE_ENVIRONMENT', '')}{os.getenv('SERVICE', '')}-s@{get_project_id()}.iam.gserviceaccount.com"
        credential_scope = f"{datestamp}/auto/storage/goog4_request"
        credential = f"{service_account_email}/{credential_scope}"
        host = f"{bucket}.storage.googleapis.com"

        canonical_headers = {"host": host}
        if method == "PUT":
            canonical_headers["content-type"] = content_type
        canonical_headers_formatted = "\n".join(sorted([f"{k}:{v}" for k, v in canonical_headers.items()])) + "\n"

        signed_headers = ";".join(sorted([key.lower() for key in canonical_headers]))
        query_parameters = {
            "X-Goog-Algorithm": "GOOG4-RSA-SHA256",
            "X-Goog-Credential": credential,
            "X-Goog-Date": request_timestamp,
            "X-Goog-Expires": expiration,
            "X-Goog-SignedHeaders": signed_headers,
        }

        canonical_query_string = "&".join(
            [f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in query_parameters.items()]
        )
        canonical_request = "\n".join(
            [
                method,
                canonical_uri,
                canonical_query_string,
                canonical_headers_formatted,
                signed_headers,
                "UNSIGNED-PAYLOAD",
            ]
        )
        canonical_request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()

        string_to_sign = "\n".join(["GOOG4-RSA-SHA256", request_timestamp, credential_scope, canonical_request_hash])
        signed_blob_response = await self.iam_client.sign_blob(
            service_account_email=service_account_email, blob=string_to_sign.encode()
        )
        signature = base64.b64decode(signed_blob_response.signed_blob).hex()
        signed_url = f"https://{host}{canonical_uri}?{canonical_query_string}&x-goog-signature={signature}"

        return signed_url
