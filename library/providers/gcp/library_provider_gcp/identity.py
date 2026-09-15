import functools
import os
from typing import Any

import httpx

from library_provider_gcp.cloud.constants import REGION
from library_provider_gcp.cloud.iam import IAM
from library_provider_gcp.cloud.project import get_project_id

SERVICE_ACCOUNT_KEYS_URL = "https://www.googleapis.com/robot/v1/metadata/x509"


class GcpIdentity:
    def __init__(self) -> None:
        self._iam = IAM()

    def service_identity(self, *, service: str) -> str:
        return f"{os.getenv('FEATURE_ENVIRONMENT', '')}{service}-s@{get_project_id()}.iam.gserviceaccount.com"

    async def sign_jwt(self, *, identity: str, payload: dict[str, Any]) -> str:
        signed = await self._iam.sign_jwt(service_account_email=identity, payload=payload)
        return signed.signed_jwt

    async def id_token(self, *, identity: str, audience: str) -> str:
        return await self._iam.generate_id_token(service_account_email=identity, audience=audience)

    async def verifying_keys(self, *, identity: str, refresh: bool = False) -> dict[str, str]:
        if refresh:
            _fetch_service_account_keys.cache_clear()
        return _fetch_service_account_keys(identity)


class GcpRuntimeContext:
    def get_deployment_id(self) -> str:
        return get_project_id()

    def get_region(self) -> str:
        return REGION

    def scope_resource_name(self, resource_name: str, /) -> str:
        return os.getenv("FEATURE_ENVIRONMENT", "") + resource_name


@functools.cache
def _fetch_service_account_keys(service_account_email: str, /) -> dict[str, str]:
    response = httpx.get(f"{SERVICE_ACCOUNT_KEYS_URL}/{service_account_email}")
    return response.json()
