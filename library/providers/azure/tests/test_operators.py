import base64
import json
from typing import Any

import pytest

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.operators import CLIENT_PRINCIPAL_HEADER, EasyAuthOperatorAuth

OBJECT_ID = "00000000-0000-0000-0000-000000000001"
EMAIL = "engineer@acme.example.com"
OBJECT_ID_CLAIM = "http://schemas.microsoft.com/identity/claims/objectidentifier"
UPN_CLAIM = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn"


def _principal(claims: dict[str, str], /) -> str:
    payload: dict[str, Any] = {"claims": [{"typ": name, "val": value} for name, value in claims.items()]}
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _header(claims: dict[str, str], /) -> dict[str, str]:
    return {CLIENT_PRINCIPAL_HEADER: _principal(claims)}


async def _refused(headers: dict[str, str]) -> InfrastructureErrorType:
    with pytest.raises(InfrastructureError) as error:
        await EasyAuthOperatorAuth().authenticate(headers=headers)
    return error.value.error_type


class TestClientPrincipal:
    async def test_the_modern_claim_names_identify_the_operator(self) -> None:
        operator = await EasyAuthOperatorAuth().authenticate(
            headers=_header({"oid": OBJECT_ID, "preferred_username": EMAIL})
        )

        assert operator.subject == OBJECT_ID
        assert operator.email == EMAIL

    async def test_the_schema_claim_names_identify_the_operator(self) -> None:
        operator = await EasyAuthOperatorAuth().authenticate(
            headers=_header({OBJECT_ID_CLAIM: OBJECT_ID, UPN_CLAIM: EMAIL})
        )

        assert operator.subject == OBJECT_ID
        assert operator.email == EMAIL

    async def test_the_first_matching_claim_wins(self) -> None:
        operator = await EasyAuthOperatorAuth().authenticate(
            headers=_header({"oid": OBJECT_ID, "preferred_username": EMAIL, "emails": "other@acme.example.com"})
        )

        assert operator.email == EMAIL


class TestRefusals:
    async def test_a_missing_header_fails_closed(self) -> None:
        assert await _refused({}) == InfrastructureErrorType.OAUTH_ERROR

    async def test_an_unreadable_header_is_refused(self) -> None:
        assert await _refused({CLIENT_PRINCIPAL_HEADER: "not-base64-json"}) == InfrastructureErrorType.OAUTH_ERROR

    async def test_a_principal_without_an_email_is_refused(self) -> None:
        assert await _refused(_header({"oid": OBJECT_ID})) == InfrastructureErrorType.OAUTH_ERROR

    async def test_a_principal_without_a_subject_is_refused(self) -> None:
        assert await _refused(_header({"preferred_username": EMAIL})) == InfrastructureErrorType.OAUTH_ERROR
