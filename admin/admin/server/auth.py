import os
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Request

from library.application.audit.context import set_actor
from library.domain.audit.actor import AuditActor, AuditActorType
from library.infrastructure.cloud.compute import Compute
from library.infrastructure.cloud.constants import PROJECT_NUMBERS_BY_ID
from library.infrastructure.cloud.project import get_project_id
from library.presentation.errors import PresentationError, PresentationErrorType

IAP_ASSERTION_HEADER = "x-goog-iap-jwt-assertion"
IAP_ISSUER = "https://cloud.google.com/iap"
IAP_JWKS_URL = "https://www.gstatic.com/iap/verify/public_key-jwk"

_signing_keys: dict[str, Any] = {}
_audience: str | None = None


@dataclass(frozen=True)
class Operator:
    subject: str
    email: str


async def require_operator(request: Request) -> Operator:
    assertion = request.headers.get(IAP_ASSERTION_HEADER)
    if not assertion:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message="Missing IAP assertion header.",
            public_message="Requests must arrive through Identity-Aware Proxy.",
        )

    operator = await _verify_assertion(assertion)

    if operator.email not in _staff_allowlist():
        raise PresentationError(
            error_type=PresentationErrorType.AUTHORIZATION_ERROR,
            message=f"{operator.email} is not on the staff allowlist.",
            public_message="This identity is not authorized for admin operations.",
        )

    set_actor(
        AuditActor(
            actor_type=AuditActorType.OPERATOR,
            actor_id=operator.subject,
            actor_email=operator.email,
            actor_role=None,
            impersonated_by=None,
        )
    )
    return operator


async def _verify_assertion(assertion: str) -> Operator:
    try:
        header = jwt.get_unverified_header(assertion)
        key = await _signing_key(header.get("kid"))
        payload = jwt.decode(
            assertion,
            key,
            algorithms=["ES256"],
            issuer=IAP_ISSUER,
            audience=await _expected_audience(),
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except PresentationError:
        raise
    except Exception as error:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message=f"Invalid IAP assertion: {error}",
            public_message="Invalid IAP assertion.",
        ) from error

    email = payload.get("email")
    subject = payload.get("sub")
    if not email or not subject:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message="IAP assertion is missing identity claims.",
            public_message="Invalid IAP assertion.",
        )
    return Operator(subject=subject, email=email)


async def _signing_key(kid: str | None) -> Any:
    if kid not in _signing_keys:
        _signing_keys.clear()
        _signing_keys.update(await _fetch_signing_keys())

    if kid is None or kid not in _signing_keys:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message=f"Unknown IAP signing key: {kid}.",
            public_message="Invalid IAP assertion.",
        )
    return jwt.PyJWK(_signing_keys[kid]).key


async def _fetch_signing_keys() -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(IAP_JWKS_URL)
        response.raise_for_status()
        return {key["kid"]: key for key in response.json()["keys"]}


async def _expected_audience() -> str:
    global _audience
    if _audience is None:
        project = get_project_id()
        backend_service = await Compute().get_backend_service(
            project=project, name=os.environ["IAP_BACKEND_SERVICE_NAME"]
        )
        _audience = f"/projects/{PROJECT_NUMBERS_BY_ID[project]}/global/backendServices/{backend_service.id}"
    return _audience


def _staff_allowlist() -> frozenset[str]:
    return frozenset(entry.strip() for entry in os.getenv("STAFF_ALLOWLIST", "").split(",") if entry.strip())
