"""ClerkSeedClient: extends the production ClerkClient with the organization- and user-creation
calls the seed needs (the base client only reads users and manages metadata).
"""

from __future__ import annotations

import os
from http import HTTPMethod
from typing import Any

import httpx

from admin.common.logger import logger
from library.domain.value_objects.users import OrganizationID, UserID
from library.infrastructure.users import ClerkClient


class ClerkSeedClient(ClerkClient):
    async def create_organization(self, *, name: str, created_by: UserID) -> OrganizationID:
        response = await self._request(
            method=HTTPMethod.POST,
            path="/organizations",
            json={"name": name, "created_by": str(created_by)},
        )
        return OrganizationID(response.json()["id"])

    async def get_or_create_user(self, *, email: str, first_name: str, last_name: str) -> UserID:
        existing = await self._find_user_by_email(email)
        if existing is not None:
            return existing
        response = await self._request(
            method=HTTPMethod.POST,
            path="/users",
            json={
                "email_address": [email],
                "first_name": first_name,
                "last_name": last_name,
                "skip_password_checks": True,
                "skip_password_requirement": True,
            },
        )
        return UserID(response.json()["id"])

    async def get_membership_role(self, *, organization_id: OrganizationID, user_id: UserID) -> str | None:
        response = await self._request(
            method=HTTPMethod.GET,
            path=f"/organizations/{organization_id}/memberships",
            params={"user_id": [str(user_id)]},
        )
        memberships = response.json().get("data", [])
        if not memberships:
            return None
        return str(memberships[0]["role"])

    async def add_to_organization(
        self, *, organization_id: OrganizationID, user_id: UserID, role: str = "org:member"
    ) -> None:
        if await self.get_membership_role(organization_id=organization_id, user_id=user_id) is not None:
            logger.info("User %s already in organization %s", user_id, organization_id)
            return
        await self._request(
            method=HTTPMethod.POST,
            path=f"/organizations/{organization_id}/memberships",
            json={"user_id": str(user_id), "role": role},
        )

    async def _find_user_by_email(self, email: str, /) -> UserID | None:
        response = await self._request(method=HTTPMethod.GET, path="/users", params={"email_address": [email]})
        data = response.json()
        if isinstance(data, list) and data:
            return UserID(data[0]["id"])
        return None

    async def _request(
        self,
        *,
        method: HTTPMethod,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY', '')}"},
            transport=httpx.AsyncHTTPTransport(retries=self.RETRIES),
        ) as client:
            response = await client.request(method, path, params=params, json=json)
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Clerk {method} {path} -> {response.status_code}: {response.text}",
                request=response.request,
                response=response,
            )
        return response
