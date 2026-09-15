import base64
import json
from collections.abc import Mapping
from typing import Any, cast

import httpx
import jwt

from library.application.ports.operators import Operator
from library.infrastructure.control_plane import OperatorNotAuthenticatedError
from library_provider_aws.clients import client, get_region

OIDC_DATA_HEADER = "x-amzn-oidc-data"
PUBLIC_KEY_URL = "https://public-keys.auth.elb.{region}.amazonaws.com/{key_id}"

_public_keys: dict[str, str] = {}


def reset_verifying_keys() -> None:
    _public_keys.clear()


class AlbOperatorAuth:
    async def authenticate(self, *, headers: Mapping[str, str]) -> Operator:
        assertion = headers.get(OIDC_DATA_HEADER)
        if not assertion:
            raise OperatorNotAuthenticatedError("requests must arrive through the authenticating load balancer")

        try:
            key_id = _key_id_of(assertion)
            payload = jwt.decode(
                assertion,
                await _verifying_key(key_id),
                algorithms=["ES256"],
                options={"require": ["exp", "iss"], "verify_aud": False},
            )
        except Exception as error:
            raise OperatorNotAuthenticatedError(f"invalid load balancer assertion: {error}") from error

        email = payload.get("email")
        subject = payload.get("sub")
        if not email or not subject:
            raise OperatorNotAuthenticatedError("the load balancer assertion carries no identity claims")
        return Operator(subject=str(subject), email=str(email))

    async def caller_identity(self) -> str:
        async with client("sts") as sts:
            identity = cast(dict[str, Any], await sts.get_caller_identity())
        return str(identity["Arn"])


def _key_id_of(assertion: str, /) -> str:
    encoded = assertion.split(".", 1)[0]
    header = cast(dict[str, Any], json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))))
    key_id = header.get("kid")
    if not key_id:
        raise OperatorNotAuthenticatedError("the load balancer assertion names no signing key")
    return str(key_id)


async def _verifying_key(key_id: str, /) -> str:
    if key_id not in _public_keys:
        async with httpx.AsyncClient() as fetcher:
            response = await fetcher.get(PUBLIC_KEY_URL.format(region=get_region(), key_id=key_id))
            response.raise_for_status()
            _public_keys[key_id] = response.text
    return _public_keys[key_id]
