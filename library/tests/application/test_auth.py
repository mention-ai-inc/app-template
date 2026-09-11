from library._testutils.cache import FakeAsyncCache
from library._testutils.users_client import FakeUsersClient
from library.application.auth import (
    clear_organization_membership_role_cache,
    get_organization_membership_role,
    get_organization_membership_role_cache_key,
)
from library.application.users import OrganizationMembership, PublicUserData, User
from library.domain.value_objects.users import (
    OrganizationID,
    UserID,
    UserPrivateMetadata,
    UserPublicMetadata,
    UserRole,
)


async def test_get_organization_membership_role_caches_clerk_lookup() -> None:
    client = _CountingFakeUsersClient(user=_admin_user())
    cache = FakeAsyncCache()

    role_first = await get_organization_membership_role(
        users_client=client,
        cache=cache,
        user_id=_user_id(),
        organization_id=_org(),
    )
    role_second = await get_organization_membership_role(
        users_client=client,
        cache=cache,
        user_id=_user_id(),
        organization_id=_org(),
    )

    assert role_first == UserRole.ADMIN
    assert role_second == UserRole.ADMIN
    assert client.get_user_calls == 1


async def test_clear_organization_membership_role_cache_forces_fresh_lookup() -> None:
    client = _CountingFakeUsersClient(user=_admin_user())
    cache = FakeAsyncCache()

    await get_organization_membership_role(
        users_client=client,
        cache=cache,
        user_id=_user_id(),
        organization_id=_org(),
    )
    await clear_organization_membership_role_cache(cache=cache, user_id=_user_id(), organization_id=_org())
    await get_organization_membership_role(
        users_client=client,
        cache=cache,
        user_id=_user_id(),
        organization_id=_org(),
    )

    assert client.get_user_calls == 2


def _org() -> OrganizationID:
    return OrganizationID("org_test")


def _user_id() -> UserID:
    return UserID("user_test")


def _admin_user() -> User:
    return User(
        id=_user_id(),
        email="admin@example.com",
        public_user_data=PublicUserData(first_name="Admin", last_name="User"),
        organizations=[
            OrganizationMembership(
                organization_id=_org(),
                role=UserRole.ADMIN,
                public_metadata=UserPublicMetadata(),
                private_metadata=UserPrivateMetadata(),
            )
        ],
    )


class _CountingFakeUsersClient(FakeUsersClient):
    def __init__(self, *, user: User) -> None:
        super().__init__(users={user.id: user})
        self.get_user_calls = 0

    async def get_user(self, *, user_id: UserID) -> User:
        self.get_user_calls += 1
        return await super().get_user(user_id=user_id)


def test_get_organization_membership_role_cache_key_is_scoped_to_user_and_org() -> None:
    key = get_organization_membership_role_cache_key(user_id=_user_id(), organization_id=_org())

    assert str(key).endswith(f"org_membership_role:{_user_id()}")
