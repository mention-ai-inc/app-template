from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.dependencies import get_auditor
from library.application.ports.users import IUsersClient
from library.presentation.dependencies import get_users_client

router = APIRouter(tags=["Organizations"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]
UsersClientDependency = Annotated[IUsersClient, Depends(get_users_client)]


class OrganizationSummary(BaseModel):
    id: str
    name: str
    slug: str


class OrganizationsResponse(BaseModel):
    organizations: list[OrganizationSummary]


@router.get("/organizations")
async def list_organizations(auditor: AuditorDependency, users_client: UsersClientDependency) -> OrganizationsResponse:
    async with auditor.operation(operation="organizations.list", organization_id=None, parameters={}):
        organizations = await users_client.list_organizations()
        return OrganizationsResponse(
            organizations=[
                OrganizationSummary(id=organization.id, name=organization.name, slug=organization.slug)
                for organization in organizations
            ]
        )
