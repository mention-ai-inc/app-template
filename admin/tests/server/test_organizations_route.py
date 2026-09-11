from collections.abc import Callable
from typing import Any

from tests.server.conftest import FakeAuditPublisher, FakeUsersClient

from library.application.users import Organization
from library.domain.audit.action import AuditAction
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPrivateMetadata,
    OrganizationPublicMetadata,
)


def _organization(*, organization_id: str, name: str, slug: str) -> Organization:
    return Organization(
        id=OrganizationID(organization_id),
        name=name,
        slug=slug,
        max_allowed_memberships=20,
        public_metadata=OrganizationPublicMetadata(),
        private_metadata=OrganizationPrivateMetadata(),
    )


async def test_list_organizations_returns_summaries_and_audits(
    client_factory: Callable[..., Any],
    users_client: FakeUsersClient,
    publisher: FakeAuditPublisher,
) -> None:
    users_client.organizations = [
        _organization(organization_id="org_beta", name="Beta Co", slug="beta"),
        _organization(organization_id="org_alpha", name="Alpha Co", slug="alpha"),
    ]

    async with client_factory() as client:
        response = await client.get("/organizations")

    assert response.status_code == 200
    assert response.json() == {
        "organizations": [
            {"id": "org_beta", "name": "Beta Co", "slug": "beta"},
            {"id": "org_alpha", "name": "Alpha Co", "slug": "alpha"},
        ]
    }
    assert [event.action for event in publisher.saved] == [
        AuditAction.ADMIN_OPERATION_REQUESTED,
        AuditAction.ADMIN_OPERATION_COMPLETED,
    ]
    assert all(event.resource_id == "organizations.list" for event in publisher.saved)
    assert all(event.organization_id is None for event in publisher.saved)


async def test_list_organizations_empty(client_factory: Callable[..., Any]) -> None:
    async with client_factory() as client:
        response = await client.get("/organizations")

    assert response.status_code == 200
    assert response.json() == {"organizations": []}
