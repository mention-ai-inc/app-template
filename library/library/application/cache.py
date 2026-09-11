import os
from typing import NewType, Protocol

from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID

CacheKey = NewType("CacheKey", str)


def get_global_cache_key(
    *, component: str, name: str, service: Service | str | None = None, namespace: str | None = None
) -> CacheKey:
    if namespace is not None:
        return CacheKey(f"{service or os.getenv('SERVICE', '')}:{component}:{namespace}:{name}")
    else:
        return CacheKey(f"{service or os.getenv('SERVICE', '')}:{component}:{name}")


def get_organizational_cache_key(
    *, organization_id: OrganizationID, component: str, service: Service | str | None
) -> CacheKey:
    return CacheKey(f"{organization_id}:{service or os.getenv('SERVICE', '')}:{component}")


class IAsyncCache(Protocol):
    async def get(self, name: str, /) -> bytes | None: ...

    async def set(
        self,
        name: str,
        value: bytes,
        /,
        *,
        ex: int | None = None,
        px: int | None = None,
        nx: bool | None = None,
        xx: bool | None = None,
    ) -> bool | None: ...

    async def delete(self, *names: str) -> int: ...
