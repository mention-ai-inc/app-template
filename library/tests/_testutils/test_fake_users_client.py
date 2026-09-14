import pytest

from library._testutils.users_client import FakeUsersClient
from library.application.ports.users import Organization, OrganizationMembership, PublicUserData, User
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPrivateMetadata,
    OrganizationPublicMetadata,
    UserID,
    UserPrivateMetadata,
    UserPublicMetadata,
    UserRole,
)


async def test_get_organization_returns_seeded_organization() -> None:
    client = FakeUsersClient.with_organization(organization_id=__org())

    organization = await client.get_organization(organization_id=__org())

    assert organization.id == __org()
    assert organization.name == "test-org"


async def test_get_user_returns_seeded_user_as_a_deep_copy() -> None:
    user = __make_user(email="member@example.com")
    client = FakeUsersClient(users={user.id: user})

    fetched = await client.get_user(user_id=user.id)
    fetched.email = "tampered@example.com"

    fetched_again = await client.get_user(user_id=user.id)
    assert fetched_again.email == "member@example.com"


async def test_update_organization_records_call_and_persists_metadata() -> None:
    client = FakeUsersClient(organizations={__org(): __make_organization()})
    new_public_metadata = OrganizationPublicMetadata()
    new_private_metadata = OrganizationPrivateMetadata()

    await client.update_organization(organization_id=__org(), public_metadata=new_public_metadata)
    await client.update_organization(organization_id=__org(), private_metadata=new_private_metadata)

    assert len(client.update_organization_calls) == 2
    assert client.update_organization_calls[0].organization_id == __org()
    assert client.update_organization_calls[0].public_metadata == new_public_metadata
    assert client.update_organization_calls[0].private_metadata is None
    assert client.update_organization_calls[1].private_metadata == new_private_metadata

    fetched = await client.get_organization(organization_id=__org())
    assert fetched.public_metadata == new_public_metadata
    assert fetched.private_metadata == new_private_metadata


async def test_invite_user_to_organization_records_call_with_all_arguments() -> None:
    client = FakeUsersClient(organizations={__org(): __make_organization()})

    await client.invite_user_to_organization(
        organization_id=__org(),
        email_address="invitee@example.com",
        role=UserRole.MEMBER,
        redirect_url="https://example.com/welcome",
    )

    assert len(client.invite_calls) == 1
    call = client.invite_calls[0]
    assert call.organization_id == __org()
    assert call.email_address == "invitee@example.com"
    assert call.role == UserRole.MEMBER
    assert call.redirect_url == "https://example.com/welcome"
    assert call.public_metadata is None


async def test_unimplemented_methods_raise_not_implemented() -> None:
    client = FakeUsersClient()

    with pytest.raises(NotImplementedError):
        await client.list_users()


def __org() -> OrganizationID:
    return OrganizationID("org_test")


def __user_id() -> UserID:
    return UserID("user_test")


def __make_organization() -> Organization:
    return Organization(
        id=__org(),
        name="test-org",
        slug="test-org",
        max_allowed_memberships=1,
        public_metadata=OrganizationPublicMetadata(),
        private_metadata=OrganizationPrivateMetadata(),
    )


def __make_user(*, email: str) -> User:
    return User(
        id=__user_id(),
        email=email,
        public_user_data=PublicUserData(first_name="Test", last_name="User"),
        organizations=[
            OrganizationMembership(
                organization_id=__org(),
                role=UserRole.MEMBER,
                public_metadata=UserPublicMetadata(),
                private_metadata=UserPrivateMetadata(),
            )
        ],
    )
