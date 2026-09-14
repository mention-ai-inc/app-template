import asyncio
import logging
import os
import random
from enum import StrEnum
from http import HTTPMethod
from typing import Any

import httpx
from pydantic import BaseModel

from library.application.ports.users import (
    IUsersClient,
    Organization,
    OrganizationMembership,
    PublicUserData,
    User,
)
from library.domain.audit.action import AuditAction
from library.domain.audit.change import FieldChange
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPrivateMetadata,
    OrganizationPublicMetadata,
    UserID,
    UserPrivateMetadata,
    UserPublicMetadata,
    UserRole,
)
from library.infrastructure.audit.publisher import record_audit_best_effort
from library.infrastructure.concurrency import map_limit
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.service import InfrastructureService
from library.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)

FEATURE_ENVIRONMENT = os.getenv("FEATURE_ENVIRONMENT", "")

_TRANSIENT_CLERK_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class ClerkRole(StrEnum):
    MEMBER = "org:member"
    ADMIN = "org:admin"

    def get_user_role(self) -> UserRole:
        match self:
            case ClerkRole.MEMBER:
                return UserRole.MEMBER
            case ClerkRole.ADMIN:
                return UserRole.ADMIN


class ClerkError(BaseModel):
    code: str
    error_type: InfrastructureErrorType
    public_message: str


class ClerkClient(IUsersClient, InfrastructureService):
    MAX_PAGE_SIZE = 100
    BASE_URL = "https://api.clerk.com/v1"
    RETRIES = 3
    RATE_LIMIT_RETRY_ATTEMPTS = 4
    RATE_LIMIT_RETRY_BASE_DELAY_SECONDS = 1.0
    LIST_ORGANIZATION_USERS_CONCURRENCY_LIMIT = 10

    async def list_organizations(self) -> list[Organization]:
        all_organizations: list[Organization] = []
        offset = 0

        while True:
            params = {"limit": self.MAX_PAGE_SIZE, "offset": offset}
            response = await self.__make_request(method=HTTPMethod.GET, path="/organizations", params=params)

            data = response.json()["data"]
            if len(data) == 0:
                break

            for organization in data:
                clerk_organization = Organization.from_organization_data(data=organization)
                all_organizations.append(clerk_organization)

            if len(data) < self.MAX_PAGE_SIZE:
                break

            offset += self.MAX_PAGE_SIZE

        return all_organizations

    async def get_organization(self, *, organization_id: OrganizationID) -> Organization:
        response = await self.__make_request(method=HTTPMethod.GET, path=f"/organizations/{organization_id}")
        data = response.json()
        return Organization.from_organization_data(data=data)

    async def update_organization(
        self,
        *,
        organization_id: OrganizationID,
        public_metadata: OrganizationPublicMetadata | None = None,
        private_metadata: OrganizationPrivateMetadata | None = None,
    ) -> None:
        if public_metadata is not None:
            await self.__make_request(
                method=HTTPMethod.PATCH,
                path=f"/organizations/{organization_id}/metadata",
                json={"public_metadata": {FEATURE_ENVIRONMENT: public_metadata.model_dump()}},
            )
        if private_metadata is not None:
            await self.__make_request(
                method=HTTPMethod.PATCH,
                path=f"/organizations/{organization_id}/metadata",
                json={"private_metadata": {FEATURE_ENVIRONMENT: private_metadata.model_dump()}},
            )

    async def clear_organization_metadata(self, *, organization_id: OrganizationID) -> None:
        await self.__make_request(
            method=HTTPMethod.PATCH,
            path=f"/organizations/{organization_id}/metadata",
            json={
                "public_metadata": {FEATURE_ENVIRONMENT: None},
                "private_metadata": {FEATURE_ENVIRONMENT: None},
            },
        )

    async def list_users(self) -> list[User]:
        users: list[User] = []
        offset = 0

        while True:
            users_response = await self.__make_request(
                method=HTTPMethod.GET, path="/users", params={"limit": self.MAX_PAGE_SIZE, "offset": offset}
            )
            if len(users_response.json()) == 0:
                break

            for user in users_response.json():
                user_id = user["id"]
                memberships = await self.__list_user_organization_memberships(user_id=UserID(user_id))

                user = User(
                    id=user_id,
                    email=self.__get_email_address(user_data=user),
                    public_user_data=PublicUserData(first_name=user["first_name"], last_name=user["last_name"]),
                    organizations=memberships,
                )
                users.append(user)

            offset += min(len(users_response.json()), self.MAX_PAGE_SIZE)

        return users

    async def list_organization_member_user_ids(
        self, *, organization_id: OrganizationID, role: UserRole | None = None
    ) -> list[UserID]:
        user_ids: list[UserID] = []
        offset = 0

        while True:
            response = await self.__make_request(
                method=HTTPMethod.GET,
                path=f"/organizations/{organization_id}/memberships",
                params={"limit": self.MAX_PAGE_SIZE, "offset": offset},
            )
            memberships = response.json()["data"]
            if len(memberships) == 0:
                break

            for membership in memberships:
                if role is not None and UserRole(membership["role"].replace("org:", "")) != role:
                    continue
                user_ids.append(UserID(membership["public_user_data"]["user_id"]))

            if len(memberships) < self.MAX_PAGE_SIZE:
                break

            offset += self.MAX_PAGE_SIZE

        return user_ids

    async def list_organization_users(self, *, organization_id: OrganizationID) -> list[User]:
        memberships_response = await self.__make_request(
            method=HTTPMethod.GET,
            path=f"/organizations/{organization_id}/memberships",
            params={"limit": self.MAX_PAGE_SIZE},
        )

        memberships = memberships_response.json()["data"]
        users: list[User] = []

        user_responses = await map_limit(
            *[self.get_user(user_id=membership["public_user_data"]["user_id"]) for membership in memberships],
            limit=self.LIST_ORGANIZATION_USERS_CONCURRENCY_LIMIT,
        )

        for membership, user_data in zip(memberships, user_responses):
            clerk_user = User(
                id=user_data.id,
                email=user_data.email,
                public_user_data=PublicUserData(
                    first_name=user_data.public_user_data.first_name, last_name=user_data.public_user_data.last_name
                ),
                organizations=[OrganizationMembership.from_membership_data(data=membership)],
            )
            users.append(clerk_user)

        return users

    async def list_organization_member_names(self, *, organization_id: OrganizationID) -> list[PublicUserData]:
        member_names: list[PublicUserData] = []
        offset = 0

        while True:
            response = await self.__make_request(
                method=HTTPMethod.GET,
                path=f"/organizations/{organization_id}/memberships",
                params={"limit": self.MAX_PAGE_SIZE, "offset": offset},
            )

            memberships = response.json()["data"]
            for membership in memberships:
                public_user_data = membership["public_user_data"]
                member_names.append(
                    PublicUserData(
                        first_name=public_user_data.get("first_name"),
                        last_name=public_user_data.get("last_name"),
                    )
                )

            if len(memberships) < self.MAX_PAGE_SIZE:
                break

            offset += self.MAX_PAGE_SIZE

        return member_names

    async def get_user(self, *, user_id: UserID) -> User:
        user_response = await self.__make_request(method=HTTPMethod.GET, path=f"/users/{user_id}")
        user_data = user_response.json()

        user = User(
            id=user_id,
            email=self.__get_email_address(user_data=user_data),
            public_user_data=PublicUserData(first_name=user_data["first_name"], last_name=user_data["last_name"]),
            organizations=await self.__list_user_organization_memberships(user_id=user_id),
        )
        return user

    async def update_user(
        self,
        *,
        user_id: UserID,
        organization_id: OrganizationID,
        public_metadata: UserPublicMetadata | None = None,
        private_metadata: UserPrivateMetadata | None = None,
    ) -> None:
        if public_metadata is not None:
            await self.__make_request(
                method=HTTPMethod.PATCH,
                path=f"/organizations/{organization_id}/memberships/{user_id}/metadata",
                json={"public_metadata": {FEATURE_ENVIRONMENT: public_metadata.model_dump()}},
            )
        if private_metadata is not None:
            await self.__make_request(
                method=HTTPMethod.PATCH,
                path=f"/organizations/{organization_id}/memberships/{user_id}/metadata",
                json={"private_metadata": {FEATURE_ENVIRONMENT: private_metadata.model_dump()}},
            )

    async def clear_user_metadata(self, *, user_id: UserID, organization_id: OrganizationID) -> None:
        await self.__make_request(
            method=HTTPMethod.PATCH,
            path=f"/organizations/{organization_id}/memberships/{user_id}/metadata",
            json={
                "public_metadata": {FEATURE_ENVIRONMENT: None},
                "private_metadata": {FEATURE_ENVIRONMENT: None},
            },
        )

    async def delete_user(self, *, user_id: UserID) -> None:
        await self.__make_request(method=HTTPMethod.DELETE, path=f"/users/{user_id}")

    async def remove_user_from_organization(self, *, organization_id: OrganizationID, user_id: UserID) -> None:
        await self.__make_request(
            method=HTTPMethod.DELETE, path=f"/organizations/{organization_id}/memberships/{user_id}"
        )
        await record_audit_best_effort(
            action=AuditAction.MEMBER_REMOVED,
            resource_type="OrganizationMembership",
            resource_id=user_id,
            organization_id=organization_id,
            changes=None,
        )

    async def invite_user_to_organization(
        self,
        *,
        organization_id: OrganizationID,
        email_address: str,
        role: UserRole,
        redirect_url: str | None = None,
        public_metadata: UserPublicMetadata | None = None,
    ) -> None:
        body: dict[str, Any] = {
            "email_address": email_address,
            "role": self.__user_role_to_clerk_role(user_role=role),
        }

        if redirect_url is not None:
            body["redirect_url"] = redirect_url

        if public_metadata is not None:
            body["public_metadata"] = {FEATURE_ENVIRONMENT: public_metadata.model_dump()}

        await self.__make_request(
            method=HTTPMethod.POST,
            path=f"/organizations/{organization_id}/invitations",
            json=body,
            expected_errors=[
                ClerkError(
                    code="already_a_member_in_organization",
                    error_type=InfrastructureErrorType.INTEGRATION_ERROR,
                    public_message=f"{email_address} has already been invited to the organization.",
                )
            ],
        )
        await record_audit_best_effort(
            action=AuditAction.MEMBER_INVITED,
            resource_type="OrganizationMembership",
            resource_id=email_address,
            organization_id=organization_id,
            changes=[FieldChange(field="role", before=None, after=role, value_captured=True)],
        )

    async def __make_request(
        self,
        *,
        method: HTTPMethod,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        expected_errors: list[ClerkError] | None = None,
    ) -> httpx.Response:
        public_error_message = "There was a problem with the authentication provider. Please try again."

        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient(
                    base_url=self.BASE_URL,
                    headers={"Authorization": f"Bearer {os.getenv('CLERK_SECRET_KEY', '')}"},
                    transport=httpx.AsyncHTTPTransport(retries=self.RETRIES),
                ) as client:
                    response = await client.request(method, path, params=params, json=json)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as error:
                attempt += 1
                if (
                    error.response.status_code in _TRANSIENT_CLERK_STATUS_CODES
                    and attempt < self.RATE_LIMIT_RETRY_ATTEMPTS
                ):
                    delay = self.__rate_limit_retry_delay(response=error.response, attempt=attempt)
                    logger.warning(
                        f"Transient Clerk error ({error.response.status_code}) on {method} {path} "
                        f"(attempt {attempt}/{self.RATE_LIMIT_RETRY_ATTEMPTS}); retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                try:
                    errors = error.response.json()["errors"]
                except ValueError:
                    raise InfrastructureError(
                        error_type=InfrastructureErrorType.INTEGRATION_ERROR,
                        message=f"Error from Clerk ({error.response.status_code}): {error.response.text}",
                        public_message=public_error_message,
                    )
                if len(errors) == 0:
                    raise InfrastructureError(
                        error_type=InfrastructureErrorType.INTEGRATION_ERROR,
                        message=f"Error from Clerk: {error.response.text}",
                        public_message=public_error_message,
                    )

                code = errors[0]["code"]
                for expected_error in expected_errors or []:
                    if expected_error.code == code:
                        return error.response

                raise InfrastructureError(
                    message=f"Error from Clerk: {error.response.text}",
                    public_message=public_error_message,
                    error_type=InfrastructureErrorType.INTEGRATION_ERROR,
                )

    def __rate_limit_retry_delay(self, *, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return self.RATE_LIMIT_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)

    def __get_email_address(self, *, user_data: dict[str, Any]) -> str:
        email = next(
            (
                email_address["email_address"]
                for email_address in user_data["email_addresses"]
                if email_address["id"] == user_data["primary_email_address_id"]
            ),
            None,
        )
        if email is None:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.INTEGRATION_ERROR,
                message=f"User {user_data['id']} has no email address",
            )
        return email

    def __user_role_to_clerk_role(self, *, user_role: UserRole) -> ClerkRole:
        match user_role:
            case UserRole.ADMIN:
                return ClerkRole.ADMIN
            case UserRole.MEMBER:
                return ClerkRole.MEMBER

    async def __list_user_organization_memberships(self, *, user_id: UserID) -> list[OrganizationMembership]:
        memberships: list[OrganizationMembership] = []
        offset = 0

        while True:
            response = await self.__make_request(
                method=HTTPMethod.GET,
                path=f"/users/{user_id}/organization_memberships",
                params={"limit": self.MAX_PAGE_SIZE, "offset": offset},
            )
            data = response.json()["data"]
            if len(data) == 0:
                break

            for membership in data:
                memberships.append(OrganizationMembership.from_membership_data(data=membership))

            if len(data) < self.MAX_PAGE_SIZE:
                break

            offset += self.MAX_PAGE_SIZE

        return memberships
