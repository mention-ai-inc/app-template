"""`SeedClient`: a thin async HTTP client for the notes service's REST API on a feature environment.

Every request carries the admin impersonation Bearer token AND a `Referer` ending in `/docs` — the
API only consults the impersonation JWT when both are present (`library.presentation.auth.user`).
The impersonation token is short-lived, so a `401` triggers one re-mint + retry.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from http import HTTPMethod
from typing import Any

import httpx

from admin.common.logger import logger
from admin.seed.auth import mint_impersonation_token
from library.conventions import DOMAIN
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID, UserID

_TIMEOUT_SECONDS = 120.0


class SeedClient:
    def __init__(
        self,
        *,
        service: Service,
        feature_environment: str,
        token: str,
        mint: Callable[[], Awaitable[str]],
    ) -> None:
        self._service = service
        base = f"https://{feature_environment}api.{DOMAIN}/rest/{service.value}"
        self._referer = f"{base}/docs"
        self._mint = mint
        self._token = token
        self._client = httpx.AsyncClient(base_url=base, timeout=_TIMEOUT_SECONDS)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, /, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._request(HTTPMethod.GET, path, params=params)
        return response.json()

    async def post(self, path: str, /, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._request(HTTPMethod.POST, path, json=json)
        return response.json()

    async def _request(
        self,
        method: HTTPMethod,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        response = await self._client.request(method, path, json=json, params=params, headers=self.__headers())
        if response.status_code == 401:
            logger.info("Token rejected (401) on %s %s; re-minting", method, path)
            self._token = await self._mint()
            response = await self._client.request(method, path, json=json, params=params, headers=self.__headers())
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{method} /rest/{self._service.value}{path} -> {response.status_code}: {response.text}",
                request=response.request,
                response=response,
            )
        return response

    def __headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Referer": self._referer}


@asynccontextmanager
async def build_client(
    *,
    feature_environment: str,
    organization_id: OrganizationID,
    admin_user_id: UserID,
    token: str,
) -> AsyncGenerator[SeedClient]:
    async def mint() -> str:
        return await mint_impersonation_token(organization_id=organization_id, user_id=admin_user_id)

    client = SeedClient(service=Service.NOTES, feature_environment=feature_environment, token=token, mint=mint)
    try:
        yield client
    finally:
        await client.aclose()
