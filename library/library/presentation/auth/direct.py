import base64
import functools
import logging
import os
from typing import Any, cast

import httpx
import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.security import HTTPAuthorizationCredentials
from jwt.algorithms import RSAPublicKey

from library.application.auth import get_organization_membership_role
from library.application.ports.cache import IAsyncCache
from library.application.ports.users import IUsersClient, User
from library.domain.value_objects.users import OrganizationID, OrganizationPublicMetadata, UserID, UserRole
from library.infrastructure.cloud.constants import FEATURE_PROJECT_ID, PRODUCTION_PROJECT_ID
from library.infrastructure.cloud.project import get_project_id
from library.infrastructure.users import ClerkRole
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.auth.types import AuthenticatedUser
from library.presentation.errors import PresentationError, PresentationErrorType

logger = logging.getLogger(SIMPLE_LOGGER_NAME)
FEATURE_ENVIRONMENT = os.getenv("FEATURE_ENVIRONMENT", "")
JWK_DOMAINS_BY_PROJECT = {
    PRODUCTION_PROJECT_ID: "https://clerk.acme.example.com/.well-known/jwks.json",
    FEATURE_PROJECT_ID: "https://your-instance.clerk.accounts.dev/.well-known/jwks.json",
}


async def get_direct_user(
    *,
    token: HTTPAuthorizationCredentials,
    users_client: IUsersClient,
    cache: IAsyncCache,
) -> AuthenticatedUser:
    return await get_user_from_token(token.credentials, users_client=users_client, cache=cache)


async def get_user_from_token(token: str, /, *, users_client: IUsersClient, cache: IAsyncCache) -> AuthenticatedUser:
    try:
        decoded_token = __decode_token(token)
        if "organization_id" in decoded_token:  # Clerk session tokens (web/mobile)
            return AuthenticatedUser.model_validate({**decoded_token, "token": token})
        else:  # Clerk OAuth access tokens (MCP clients)
            return await __authenticated_user_from_oauth_token(
                decoded_token, token=token, users_client=users_client, cache=cache
            )
    except PresentationError:
        raise
    except Exception as error:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR, message=str(error), public_message="Invalid token"
        )


async def __authenticated_user_from_oauth_token(
    claims: dict[str, Any], *, token: str, users_client: IUsersClient, cache: IAsyncCache
) -> AuthenticatedUser:
    user_id = claims.get("sub")
    if not user_id:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message="OAuth token is missing the `sub` claim.",
            public_message="Invalid token",
        )

    org_id = claims.get("org_id")
    if org_id:
        organization_id = OrganizationID(org_id)
    else:
        user = await users_client.get_user(user_id=UserID(user_id))
        organization_id = __resolve_organization_id(claims=claims, user=user)

    clerk_role = await __resolve_clerk_role_for_oauth(
        claims=claims,
        user_id=UserID(user_id),
        organization_id=organization_id,
        users_client=users_client,
        cache=cache,
    )

    return AuthenticatedUser.model_validate(
        {
            "token": token,
            "uid": user_id,
            "organization_id": str(organization_id),
            "clerk_role": clerk_role,
            "organization_public_metadata": {FEATURE_ENVIRONMENT: OrganizationPublicMetadata().model_dump()},
        }
    )


async def __resolve_clerk_role_for_oauth(
    *,
    claims: dict[str, Any],
    user_id: UserID,
    organization_id: OrganizationID,
    users_client: IUsersClient,
    cache: IAsyncCache,
) -> ClerkRole:
    org_role = claims.get("org_role")
    if org_role == ClerkRole.ADMIN:
        return ClerkRole.ADMIN
    if org_role == ClerkRole.MEMBER:
        return ClerkRole.MEMBER

    role = await get_organization_membership_role(
        users_client=users_client,
        cache=cache,
        user_id=user_id,
        organization_id=organization_id,
    )
    return ClerkRole.ADMIN if role == UserRole.ADMIN else ClerkRole.MEMBER


def __resolve_organization_id(*, claims: dict[str, Any], user: User) -> OrganizationID:
    org_id = claims.get("org_id")
    if org_id:
        return OrganizationID(org_id)

    if len(user.organizations) == 1:
        return user.organizations[0].organization_id

    if not user.organizations:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message=f"User {user.id} is not a member of any organization.",
            public_message="Your account isn't a member of any organization.",
        )

    org_ids = ", ".join(str(membership.organization_id) for membership in user.organizations)
    raise PresentationError(
        error_type=PresentationErrorType.AUTHENTICATION_ERROR,
        message=f"User {user.id} belongs to multiple organizations ({org_ids}) but the token carries no org_id.",
        public_message=(
            "Your account belongs to multiple organizations. Connect with an OAuth client whose app has the "
            "`user:org:read` scope so you can pick one."
        ),
    )


def __decode_token(token: str, /) -> dict[str, Any]:
    jwks = __get_jwks()
    n = __base64url_decode(jwks["n"])
    e = __base64url_decode(jwks["e"])
    public_key = rsa.RSAPublicNumbers(e=int.from_bytes(e, "big"), n=int.from_bytes(n, "big")).public_key(
        backend=default_backend()
    )
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    loaded_public_key = cast(RSAPublicKey, serialization.load_pem_public_key(pem, backend=default_backend()))
    return jwt.decode(token, loaded_public_key, algorithms=["RS256"])


@functools.lru_cache
def __get_jwks() -> dict[str, Any]:
    project_id = get_project_id()
    domain = JWK_DOMAINS_BY_PROJECT[project_id]
    jwks = httpx.get(domain).json()
    jwk = jwks["keys"][0]
    return jwk


def __base64url_decode(to_decode: str, /) -> bytes:
    rem = len(to_decode) % 4
    if rem > 0:
        to_decode += "=" * (4 - rem)
    return base64.urlsafe_b64decode(to_decode)
