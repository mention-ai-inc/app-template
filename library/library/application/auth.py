from library.application.ports.cache import CacheKey, IAsyncCache, get_organizational_cache_key
from library.application.ports.users import IUsersClient
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID, UserID, UserRole

ORG_MEMBERSHIP_ROLE_CACHE_TTL_SECONDS = 300


async def get_organization_membership_role(
    *,
    users_client: IUsersClient,
    cache: IAsyncCache,
    user_id: UserID,
    organization_id: OrganizationID,
) -> UserRole:
    cache_key = get_organization_membership_role_cache_key(user_id=user_id, organization_id=organization_id)
    cached_role = await cache.get(cache_key)
    if cached_role is not None:
        return UserRole(cached_role.decode())

    user = await users_client.get_user(user_id=user_id)
    role = user.get_organization_membership(organization_id=organization_id).role
    await cache.set(cache_key, role.value.encode(), ex=ORG_MEMBERSHIP_ROLE_CACHE_TTL_SECONDS)
    return role


async def clear_organization_membership_role_cache(
    *,
    cache: IAsyncCache,
    user_id: UserID,
    organization_id: OrganizationID,
) -> None:
    await cache.delete(get_organization_membership_role_cache_key(user_id=user_id, organization_id=organization_id))


def get_organization_membership_role_cache_key(*, user_id: UserID, organization_id: OrganizationID) -> CacheKey:
    return get_organizational_cache_key(
        organization_id=organization_id,
        component=f"org_membership_role:{user_id}",
        service=Service.NOTES,
    )
