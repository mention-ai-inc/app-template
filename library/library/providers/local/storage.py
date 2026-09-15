import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from library.domain.value_objects.common import PresignedURL
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.persistence.storage import ObjectNotFoundError


@dataclass
class StoredBlob:
    content: bytes
    saved_at: datetime


@dataclass
class LocalBlobStore:
    bucket: str
    blobs: dict[str, StoredBlob] = field(default_factory=dict[str, StoredBlob])

    @staticmethod
    def org_prefix(organization_id: OrganizationID) -> str:
        return f"orgs/{organization_id}/"

    def get_path_to_blob(self, *, organization_id: OrganizationID, document_id: str, field_id: str) -> str:
        return f"{self.org_prefix(organization_id)}blobs/{document_id}/{field_id}.blob"

    def get_legacy_path_to_blob(self, *, document_id: str, field_id: str) -> str:
        return f"blobs/{document_id}/{field_id}.blob"

    async def exists(self, *, filepath: str) -> bool:
        return filepath in self.blobs

    async def insert(self, *, filepath: str, content: bytes) -> None:
        self.blobs[filepath] = StoredBlob(content=content, saved_at=datetime.now(UTC))

    async def get(self, *, filepath: str) -> bytes:
        blob = self.blobs.get(filepath)
        if blob is None:
            raise ObjectNotFoundError(filepath)
        return blob.content

    async def get_saved_at(self, *, filepath: str) -> datetime:
        blob = self.blobs.get(filepath)
        if blob is None:
            raise ObjectNotFoundError(filepath)
        return blob.saved_at

    async def delete(self, *, filepath: str) -> None:
        if self.blobs.pop(filepath, None) is None:
            raise ObjectNotFoundError(filepath)

    async def delete_all_under(self, *, prefix: str) -> None:
        for filepath in await self.list(prefix=prefix):
            await self.delete(filepath=filepath)

    async def list(self, *, prefix: str = "") -> list[str]:
        return sorted(filepath for filepath in self.blobs if filepath.startswith(prefix))

    async def get_presigned_url(
        self, *, filepath: str, expiration: int, content_type: str, method: Literal["GET", "PUT"]
    ) -> PresignedURL:
        if filepath not in self.blobs:
            await self.insert(filepath=filepath, content=b"")
        signature = hashlib.sha256(f"{self.bucket}/{filepath}/{method}/{expiration}".encode()).hexdigest()
        return PresignedURL(
            f"https://local.invalid/{self.bucket}/{filepath}"
            f"?method={method}&content_type={content_type}&expires_in={expiration}&signature={signature}"
        )


@dataclass
class LocalSecretStore:
    secrets: dict[str, str] = field(default_factory=dict[str, str])

    async def access_secret_version(self, *, secret_id: str, version_id: str = "latest") -> str:
        return self.secrets.get(secret_id, f"local-secret-{secret_id}-{version_id}")


@dataclass
class LocalIdentity:
    signing_key: str = "local-signing-key"

    def service_identity(self, *, service: str) -> str:
        return f"{service}@local.invalid"

    async def sign_jwt(self, *, identity: str, payload: dict[str, Any]) -> str:
        header = self.__encode({"alg": "none", "kid": self.signing_key, "typ": "JWT"})
        body = self.__encode({**payload, "iss": identity})
        signature = hashlib.sha256(f"{self.signing_key}.{header}.{body}".encode()).hexdigest()
        return f"{header}.{body}.{signature}"

    async def id_token(self, *, identity: str, audience: str) -> str:
        return await self.sign_jwt(identity=identity, payload={"aud": audience})

    async def verifying_keys(self, *, identity: str) -> dict[str, str]:
        return {self.signing_key: f"local-public-key-for-{identity}"}

    def __encode(self, claims: dict[str, Any], /) -> str:
        return base64.urlsafe_b64encode(json.dumps(claims, default=str, sort_keys=True).encode()).decode().rstrip("=")


@dataclass
class LocalRuntimeContext:
    deployment_id: str = "local"
    region: str = "local"

    def get_deployment_id(self) -> str:
        return self.deployment_id

    def get_region(self) -> str:
        return self.region

    def scope_resource_name(self, resource_name: str, /) -> str:
        return os.getenv("FEATURE_ENVIRONMENT", "") + resource_name
