import os
from typing import Any, Protocol

from pydantic import BaseModel

from library.domain.errors import DomainError
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPrivateMetadata,
    OrganizationPublicMetadata,
    UserID,
    UserPrivateMetadata,
    UserPublicMetadata,
    UserRole,
)

FEATURE_ENVIRONMENT = os.getenv("FEATURE_ENVIRONMENT", "")


class Organization(BaseModel):
    id: OrganizationID
    name: str
    slug: str
    max_allowed_memberships: int
    public_metadata: OrganizationPublicMetadata
    private_metadata: OrganizationPrivateMetadata

    @classmethod
    def from_organization_data(cls, *, data: dict[str, Any]) -> "Organization":
        raw_public_metadata = data["public_metadata"].get(FEATURE_ENVIRONMENT)
        raw_private_metadata = data["private_metadata"].get(FEATURE_ENVIRONMENT)

        if raw_public_metadata:
            public_metadata = OrganizationPublicMetadata.model_validate(raw_public_metadata)
        else:
            public_metadata = OrganizationPublicMetadata()

        if raw_private_metadata:
            private_metadata = OrganizationPrivateMetadata.model_validate(raw_private_metadata)
        else:
            private_metadata = OrganizationPrivateMetadata()

        return cls(
            id=OrganizationID(data["id"]),
            name=data["name"],
            slug=data["slug"],
            max_allowed_memberships=data["max_allowed_memberships"],
            public_metadata=public_metadata,
            private_metadata=private_metadata,
        )


class PublicUserData(BaseModel):
    first_name: str | None = None
    last_name: str | None = None

    @property
    def full_name(self) -> str:
        name = ""
        if self.first_name is not None:
            name += self.first_name
        if self.last_name is not None:
            name += f" {self.last_name}"
        return name.strip()


class OrganizationMembership(BaseModel):
    organization_id: OrganizationID
    role: UserRole
    public_metadata: UserPublicMetadata
    private_metadata: UserPrivateMetadata

    @classmethod
    def from_membership_data(cls, *, data: dict[str, Any]) -> "OrganizationMembership":
        raw_public_metadata = data["public_metadata"].get(FEATURE_ENVIRONMENT)
        raw_private_metadata = data["private_metadata"].get(FEATURE_ENVIRONMENT)

        if raw_public_metadata is not None:
            public_metadata = UserPublicMetadata.model_validate(raw_public_metadata)
        else:
            public_metadata = UserPublicMetadata()

        if raw_private_metadata is not None:
            private_metadata = UserPrivateMetadata.model_validate(raw_private_metadata)
        else:
            private_metadata = UserPrivateMetadata()

        return cls(
            organization_id=OrganizationID(data["organization"]["id"]),
            role=UserRole(data["role"].replace("org:", "")),
            public_metadata=public_metadata,
            private_metadata=private_metadata,
        )


class User(BaseModel):
    id: UserID
    email: str
    public_user_data: PublicUserData
    organizations: list[OrganizationMembership]

    def get_organization_membership(self, *, organization_id: OrganizationID) -> OrganizationMembership:
        for membership in self.organizations:
            if membership.organization_id == organization_id:
                return membership

        raise DomainError(
            message=f"User {self.id} is not a member of organization {organization_id}",
        )


class IUsersClient(Protocol):
    async def list_organizations(self) -> list[Organization]: ...
    async def get_organization(self, *, organization_id: OrganizationID) -> Organization: ...
    async def get_user(self, *, user_id: UserID) -> User: ...
    async def list_users(self) -> list[User]: ...
    async def list_organization_users(self, *, organization_id: OrganizationID) -> list[User]: ...
    async def list_organization_member_user_ids(
        self, *, organization_id: OrganizationID, role: UserRole | None = None
    ) -> list[UserID]: ...
    async def list_organization_member_names(self, *, organization_id: OrganizationID) -> list[PublicUserData]: ...
    async def update_organization(
        self,
        *,
        organization_id: OrganizationID,
        public_metadata: OrganizationPublicMetadata | None = None,
        private_metadata: OrganizationPrivateMetadata | None = None,
    ) -> None: ...
    async def update_user(
        self,
        *,
        user_id: UserID,
        organization_id: OrganizationID,
        public_metadata: UserPublicMetadata | None = None,
        private_metadata: UserPrivateMetadata | None = None,
    ) -> None: ...
    async def clear_user_metadata(self, *, user_id: UserID, organization_id: OrganizationID) -> None: ...
    async def delete_user(self, *, user_id: UserID) -> None: ...
    async def remove_user_from_organization(self, *, organization_id: OrganizationID, user_id: UserID) -> None: ...
    async def invite_user_to_organization(
        self,
        *,
        organization_id: OrganizationID,
        email_address: str,
        role: UserRole,
        redirect_url: str | None = None,
        public_metadata: UserPublicMetadata | None = None,
    ) -> None: ...
