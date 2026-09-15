import os
from collections.abc import Mapping
from typing import Any, cast

import google.auth
import httpx
import jwt

from library.application.ports.operators import Operator
from library.infrastructure.control_plane import OperatorNotAuthenticatedError
from library_provider_gcp.cloud.compute import Compute
from library_provider_gcp.cloud.constants import PROJECT_NUMBERS_BY_ID
from library_provider_gcp.cloud.project import get_project_id

IAP_ASSERTION_HEADER = "x-goog-iap-jwt-assertion"
IAP_ISSUER = "https://cloud.google.com/iap"
IAP_JWKS_URL = "https://www.gstatic.com/iap/verify/public_key-jwk"
BACKEND_SERVICE_VARIABLE = "IAP_BACKEND_SERVICE_NAME"

_signing_keys: dict[str, Any] = {}
_audience: str | None = None


def reset_iap_cache() -> None:
    global _audience
    _signing_keys.clear()
    _audience = None


class IapOperatorAuth:
    async def authenticate(self, *, headers: Mapping[str, str]) -> Operator:
        assertion = headers.get(IAP_ASSERTION_HEADER)
        if not assertion:
            raise OperatorNotAuthenticatedError("requests must arrive through Identity-Aware Proxy")

        try:
            header = jwt.get_unverified_header(assertion)
            payload = jwt.decode(
                assertion,
                await _signing_key(header.get("kid")),
                algorithms=["ES256"],
                issuer=IAP_ISSUER,
                audience=await _expected_audience(),
                options={"require": ["exp", "iat", "iss", "aud"]},
            )
        except Exception as error:
            raise OperatorNotAuthenticatedError(f"invalid IAP assertion: {error}") from error

        email = payload.get("email")
        subject = payload.get("sub")
        if not email or not subject:
            raise OperatorNotAuthenticatedError("the IAP assertion carries no identity claims")
        return Operator(subject=subject, email=email)

    async def caller_identity(self) -> str:
        credentials, _ = google.auth.default()
        account = cast(Any, credentials)
        return str(
            getattr(account, "service_account_email", None) or getattr(account, "_account", "") or get_project_id()
        )


async def _signing_key(kid: str | None) -> Any:
    if kid not in _signing_keys:
        _signing_keys.clear()
        _signing_keys.update(await _fetch_signing_keys())

    if kid is None or kid not in _signing_keys:
        raise OperatorNotAuthenticatedError(f"unknown IAP signing key: {kid}")
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
            project=project, name=os.environ[BACKEND_SERVICE_VARIABLE]
        )
        _audience = f"/projects/{PROJECT_NUMBERS_BY_ID[project]}/global/backendServices/{backend_service.id}"
    return _audience
