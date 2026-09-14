from typing import NamedTuple

from library.application.ports.users import (
    IUsersClient,
    Organization,
    PublicUserData,
    User,
)
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPrivateMetadata,
    OrganizationPublicMetadata,
    UserID,
    UserPrivateMetadata,
    UserPublicMetadata,
    UserRole,
)


class UpdateOrganizationCall(NamedTuple):
    organization_id: OrganizationID
    public_metadata: OrganizationPublicMetadata | None
    private_metadata: OrganizationPrivateMetadata | None


class InviteUserCall(NamedTuple):
    organization_id: OrganizationID
    email_address: str
    role: UserRole
    redirect_url: str | None
    public_metadata: UserPublicMetadata | None


class UpdateUserCall(NamedTuple):
    user_id: UserID
    organization_id: OrganizationID
    public_metadata: UserPublicMetadata | None
    private_metadata: UserPrivateMetadata | None


class FakeUsersClient(IUsersClient):
    """In-memory `IUsersClient`.

    Implements the methods that production use cases call against `IUsersClient`.
    Methods that no in-tree test exercises raise `NotImplementedError`; add
    behavior here when a flow that needs them gets covered.

    `get_organization` and `get_user` return deep copies, mirroring production's
    fresh-from-Clerk deserialization, and `get_organization` records into
    `get_organization_calls` so tests can assert how often a flow reaches Clerk.
    `update_organization` mutates the stored organization's metadata so a
    subsequent `get_organization` reflects the update, and records the call into
    `update_organization_calls`. `invite_user_to_organization` records into
    `invite_calls`.

    """

    def __init__(
        self,
        *,
        organizations: dict[OrganizationID, Organization] | None = None,
        users: dict[UserID, User] | None = None,
        organization_users: dict[OrganizationID, list[User]] | None = None,
    ) -> None:
        self._organizations = organizations or {}
        self._users = users or {}
        self._organization_users = organization_users or {}
        self.get_organization_calls: list[OrganizationID] = []
        self.update_organization_calls: list[UpdateOrganizationCall] = []
        self.invite_calls: list[InviteUserCall] = []
        self.update_user_calls: list[UpdateUserCall] = []
        self.deleted_user_ids: list[UserID] = []

    @classmethod
    def with_organization(
        cls,
        *,
        organization_id: OrganizationID,
        organization_users: dict[OrganizationID, list[User]] | None = None,
        users: dict[UserID, User] | None = None,
    ) -> "FakeUsersClient":
        return cls(
            organizations={organization_id: cls.__make_organization(organization_id)},
            organization_users=organization_users,
            users=users,
        )

    async def get_organization(self, *, organization_id: OrganizationID) -> Organization:
        self.get_organization_calls.append(organization_id)
        return self._organizations[organization_id].model_copy(deep=True)

    async def list_organizations(self) -> list[Organization]:
        return [organization.model_copy(deep=True) for organization in self._organizations.values()]

    async def get_user(self, *, user_id: UserID) -> User:
        return self._users[user_id].model_copy(deep=True)

    async def update_organization(
        self,
        *,
        organization_id: OrganizationID,
        public_metadata: OrganizationPublicMetadata | None = None,
        private_metadata: OrganizationPrivateMetadata | None = None,
    ) -> None:
        self.update_organization_calls.append(
            UpdateOrganizationCall(
                organization_id=organization_id,
                public_metadata=public_metadata.model_copy(deep=True) if public_metadata is not None else None,
                private_metadata=private_metadata.model_copy(deep=True) if private_metadata is not None else None,
            )
        )

        stored = self._organizations[organization_id]
        if public_metadata is not None:
            stored.public_metadata = public_metadata.model_copy(deep=True)
        if private_metadata is not None:
            stored.private_metadata = private_metadata.model_copy(deep=True)

    async def invite_user_to_organization(
        self,
        *,
        organization_id: OrganizationID,
        email_address: str,
        role: UserRole,
        redirect_url: str | None = None,
        public_metadata: UserPublicMetadata | None = None,
    ) -> None:
        self.invite_calls.append(
            InviteUserCall(
                organization_id=organization_id,
                email_address=email_address,
                role=role,
                redirect_url=redirect_url,
                public_metadata=public_metadata.model_copy(deep=True) if public_metadata is not None else None,
            )
        )

    async def list_users(self) -> list[User]:
        raise NotImplementedError

    async def list_organization_users(self, *, organization_id: OrganizationID) -> list[User]:
        return [user.model_copy(deep=True) for user in self._organization_users.get(organization_id, [])]

    async def list_organization_member_user_ids(
        self, *, organization_id: OrganizationID, role: UserRole | None = None
    ) -> list[UserID]:
        return [
            user.id
            for user in self._organization_users.get(organization_id, [])
            if role is None or user.get_organization_membership(organization_id=organization_id).role == role
        ]

    async def list_organization_member_names(self, *, organization_id: OrganizationID) -> list[PublicUserData]:
        return [user.public_user_data.model_copy() for user in self._organization_users.get(organization_id, [])]

    async def update_user(
        self,
        *,
        user_id: UserID,
        organization_id: OrganizationID,
        public_metadata: UserPublicMetadata | None = None,
        private_metadata: UserPrivateMetadata | None = None,
    ) -> None:
        self.update_user_calls.append(
            UpdateUserCall(
                user_id=user_id,
                organization_id=organization_id,
                public_metadata=public_metadata.model_copy(deep=True) if public_metadata is not None else None,
                private_metadata=private_metadata.model_copy(deep=True) if private_metadata is not None else None,
            )
        )

        stored = self._users.get(user_id)
        if stored is None:
            return
        for membership in stored.organizations:
            if membership.organization_id != organization_id:
                continue
            if public_metadata is not None:
                membership.public_metadata = public_metadata.model_copy(deep=True)
            if private_metadata is not None:
                membership.private_metadata = private_metadata.model_copy(deep=True)

    async def delete_user(self, *, user_id: UserID) -> None:
        self.deleted_user_ids.append(user_id)
        self._users.pop(user_id, None)
        for organization_id, users in self._organization_users.items():
            self._organization_users[organization_id] = [user for user in users if user.id != user_id]

    async def clear_user_metadata(self, *, user_id: UserID, organization_id: OrganizationID) -> None:
        raise NotImplementedError

    async def remove_user_from_organization(self, *, organization_id: OrganizationID, user_id: UserID) -> None:
        raise NotImplementedError

    @staticmethod
    def __make_organization(organization_id: OrganizationID) -> Organization:
        return Organization(
            id=organization_id,
            name="test-org",
            slug="test-org",
            max_allowed_memberships=1,
            public_metadata=OrganizationPublicMetadata(),
            private_metadata=OrganizationPrivateMetadata(),
        )
