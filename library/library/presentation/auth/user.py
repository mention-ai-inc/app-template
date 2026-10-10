import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from control_plane.application.audit.context import set_actor
from control_plane.application.ports.users import IUsersClient
from control_plane.domain.audit.actor import AuditActor, AuditActorType
from control_plane.infrastructure.persistence.cache.base import AsyncCache
from control_plane.infrastructure.users import ClerkRole
from control_plane.logs import SIMPLE_LOGGER_NAME
from control_plane.presentation.auth.impersonation import get_impersonated_user
from control_plane.presentation.auth.types import AuthenticatedUser
from control_plane.presentation.dependencies import get_cache, get_users_client
from control_plane.presentation.errors import PresentationError, PresentationErrorType
from library.presentation.auth.direct import get_direct_user

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
        user = await get_impersonated_user(token=token)
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
