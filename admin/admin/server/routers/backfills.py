import os
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.catalogue import BACKFILL_GROUP, BackfillCatalogue
from admin.server.dependencies import get_auditor, get_backfill_catalogue, get_job_launcher
from admin.server.jobs import JobLauncher
from control_plane.application.audit.context import set_source
from control_plane.application.errors import ApplicationError, ApplicationErrorType
from control_plane.application.ports.users import IUsersClient
from control_plane.domain.audit.event import AuditSource
from control_plane.presentation.dependencies import get_users_client

router = APIRouter(tags=["Backfills"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]
LauncherDependency = Annotated[JobLauncher, Depends(get_job_launcher)]
CatalogueDependency = Annotated[BackfillCatalogue, Depends(get_backfill_catalogue)]
UsersClientDependency = Annotated[IUsersClient, Depends(get_users_client)]


class BackfillSummary(BaseModel):
    name: str
    description: str


class BackfillsResponse(BaseModel):
    backfills: list[BackfillSummary]
    job_image: str | None
    commit_sha: str | None
    image_digest: str | None


class RunBackfillRequest(BaseModel):
    apply: bool = False
    organization_id: str | None = None


class LaunchedRun(BaseModel):
    execution_id: str


@router.get("/backfills")
async def list_backfills(
    launcher: LauncherDependency, catalogue: CatalogueDependency, auditor: AuditorDependency
) -> BackfillsResponse:
    async with auditor.operation(operation="backfill.list", organization_id=None, parameters={}):
        job_image = await launcher.job_image(group=BACKFILL_GROUP)
        entries = await catalogue.list()
        return BackfillsResponse(
            backfills=[BackfillSummary(name=entry.name, description=entry.description) for entry in entries],
            job_image=job_image,
            commit_sha=os.getenv("COMMIT_SHA"),
            image_digest=os.getenv("IMAGE_DIGEST"),
        )


@router.post("/backfills/{name}/runs")
async def run_backfill(
    name: str,
    request: RunBackfillRequest,
    launcher: LauncherDependency,
    catalogue: CatalogueDependency,
    auditor: AuditorDependency,
    users_client: UsersClientDependency,
) -> LaunchedRun:
    if not await catalogue.has(name):
        raise ApplicationError(
            error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
            message=f"No backfill named {name!r} exists in the deployed image.",
        )

    args = ["run", name]
    if request.apply:
        args.append("--apply")
    if request.organization_id is not None:
        args.extend(["--organization-id", request.organization_id])

    execution_id = await launcher.launch(group=BACKFILL_GROUP, args=args)

    set_source(AuditSource.JOB)
    await auditor.launch_requested(
        operation="backfill.run",
        organization_id=request.organization_id,
        parameters={"backfill": name, "apply": request.apply, "execution_id": execution_id},
        users_client=users_client,
    )
    return LaunchedRun(execution_id=execution_id)
