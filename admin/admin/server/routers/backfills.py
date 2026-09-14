import os
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from admin.backfill.registry import discover
from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.dependencies import get_auditor, get_job_launcher
from admin.server.jobs import JobLauncher
from library.application.audit.context import set_source
from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.users import IUsersClient
from library.domain.audit.event import AuditSource
from library.presentation.dependencies import get_users_client

router = APIRouter(tags=["Backfills"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]
LauncherDependency = Annotated[JobLauncher, Depends(get_job_launcher)]
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
async def list_backfills(launcher: LauncherDependency, auditor: AuditorDependency) -> BackfillsResponse:
    async with auditor.operation(operation="backfill.list", organization_id=None, parameters={}):
        job_image = await launcher.job_image(group="backfill")
        return BackfillsResponse(
            backfills=[
                BackfillSummary(name=backfill.name, description=backfill.description) for backfill in discover()
            ],
            job_image=job_image,
            commit_sha=os.getenv("COMMIT_SHA"),
            image_digest=os.getenv("IMAGE_DIGEST"),
        )


@router.post("/backfills/{name}/runs")
async def run_backfill(
    name: str,
    request: RunBackfillRequest,
    launcher: LauncherDependency,
    auditor: AuditorDependency,
    users_client: UsersClientDependency,
) -> LaunchedRun:
    if name not in {backfill.name for backfill in discover()}:
        raise ApplicationError(
            error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
            message=f"No backfill named {name!r} exists in the deployed image.",
        )

    args = ["run", name]
    if request.apply:
        args.append("--apply")
    if request.organization_id is not None:
        args.extend(["--organization-id", request.organization_id])

    execution_id = await launcher.launch(group="backfill", args=args)

    set_source(AuditSource.JOB)
    await auditor.launch_requested(
        operation="backfill.run",
        organization_id=request.organization_id,
        parameters={"backfill": name, "apply": request.apply, "execution_id": execution_id},
        users_client=users_client,
    )
    return LaunchedRun(execution_id=execution_id)
