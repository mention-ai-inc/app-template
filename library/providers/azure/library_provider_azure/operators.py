import base64
import json
from collections.abc import Mapping
from typing import Any, cast

import jwt

from library.application.ports.operators import Operator
from library.infrastructure.control_plane import OperatorNotAuthenticatedError
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import ARM_SCOPE

CLIENT_PRINCIPAL_HEADER = "x-ms-client-principal"
EMAIL_CLAIMS = (
    "preferred_username",
    "emails",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn",
)
SUBJECT_CLAIMS = (
    "http://schemas.microsoft.com/identity/claims/objectidentifier",
    "oid",
    "sub",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
)


class EasyAuthOperatorAuth:
    async def authenticate(self, *, headers: Mapping[str, str]) -> Operator:
        encoded = headers.get(CLIENT_PRINCIPAL_HEADER)
        if not encoded:
            raise OperatorNotAuthenticatedError("requests must arrive through the container app's built-in auth")

        claims = _claims_of(encoded)
        email = _first(claims, EMAIL_CLAIMS)
        subject = _first(claims, SUBJECT_CLAIMS)
        if not email or not subject:
            raise OperatorNotAuthenticatedError("the client principal carries no identity claims")
        return Operator(subject=subject, email=email)

    async def caller_identity(self) -> str:
        token = await AzureClients.credential().get_token(ARM_SCOPE)
        claims = jwt.decode(token.token, options={"verify_signature": False})
        return str(claims.get("upn") or claims.get("preferred_username") or claims.get("oid") or claims.get("appid"))


def _claims_of(encoded: str, /) -> dict[str, str]:
    try:
        principal = cast(dict[str, Any], json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4))))
    except Exception as error:
        raise OperatorNotAuthenticatedError(f"unreadable client principal: {error}") from error

    claims: dict[str, str] = {}
    for claim in cast(list[dict[str, Any]], principal.get("claims", [])):
        claim_type = claim.get("typ") or claim.get("type")
        if claim_type is not None and str(claim_type) not in claims:
            claims[str(claim_type)] = str(claim.get("val", ""))
    return claims


def _first(claims: Mapping[str, str], names: tuple[str, ...], /) -> str | None:
    for name in names:
        value = claims.get(name)
        if value:
            return value
    return None
