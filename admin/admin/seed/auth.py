"""Mint impersonation tokens for driving the product's REST API as a client.

The token is a service-account-signed JWT (`generate_impersonation_token`) carrying the given
`uid`, `organization_id`, and `clerk_role=ADMIN`. The API only takes the impersonation branch when
the request also sends a `Referer` ending in `/docs` (see `library.presentation.auth.user`), so the
`SeedClient` always pairs this token with that header.
"""

from __future__ import annotations

from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID, UserID
from library.presentation.auth.impersonation import generate_impersonation_token


async def mint_impersonation_token(*, organization_id: OrganizationID, user_id: UserID) -> str:
    return await generate_impersonation_token(
        calling_service=Service.NOTES.value,
        user_id=str(user_id),
        organization_id=str(organization_id),
    )
