import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from library.application.audit.context import set_actor
from library.application.users import IUsersClient
from library.domain.audit.actor import AuditActor, AuditActorType
from library.infrastructure.persistence.cache.base import AsyncCache
from library.infrastructure.users import ClerkRole
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.auth.direct import get_direct_user
from library.presentation.auth.impersonation import get_impersonated_user
from library.presentation.auth.types import AuthenticatedUser
from library.presentation.dependencies import get_cache, get_users_client
from library.presentation.errors import PresentationError, PresentationErrorType

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


async def get_user(
    *,
    request: Request,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    users_client: IUsersClient = Depends(get_users_client),
    cache: AsyncCache = Depends(get_cache),
) -> AuthenticatedUser:
    referer = request.headers.get("Referer", "")
    is_impersonation = ("api." in referer or "localhost" in referer) and referer.endswith("/docs")

    if is_impersonation:
        user = get_impersonated_user(token=token)
    else:
        user = await get_direct_user(token=token, users_client=users_client, cache=cache)

    set_actor(_to_audit_actor(user))
    return user


async def get_admin_user(
    *,
    request: Request,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    users_client: IUsersClient = Depends(get_users_client),
    cache: AsyncCache = Depends(get_cache),
) -> AuthenticatedUser:
    user = await get_user(request=request, token=token, users_client=users_client, cache=cache)
    if user.clerk_role != ClerkRole.ADMIN:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHORIZATION_ERROR, message="This action is admin-only."
        )
    return user


def _to_audit_actor(user: AuthenticatedUser) -> AuditActor:
    return AuditActor(
        actor_type=AuditActorType.USER,
        actor_id=user.uid,
        actor_email=None,
        actor_role=user.user_role,
        impersonated_by=user.impersonating_service,
    )
