from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.dependencies import get_auditor, get_job_launcher
from admin.server.jobs import JobLauncher
from library.application.audit.context import set_source
from library.domain.audit.event import AuditSource
from library.domain.value_objects.users import OrganizationID

router = APIRouter(prefix="/seed", tags=["Seed"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]
LauncherDependency = Annotated[JobLauncher, Depends(get_job_launcher)]


class SeedRunRequest(BaseModel):
    organization_id: str | None = None


class LaunchedRun(BaseModel):
    execution_id: str


@router.post("/runs")
async def run_seed(request: SeedRunRequest, launcher: LauncherDependency, auditor: AuditorDependency) -> LaunchedRun:
    args = ["run"]
    if request.organization_id is not None:
        args.extend(["--organization-id", request.organization_id])

    execution_id = await launcher.launch(group="seed", args=args)

    set_source(AuditSource.JOB)
    await auditor.operation_requested(
        operation="seed.run",
        organization_id=OrganizationID(request.organization_id) if request.organization_id else None,
        parameters={"execution_id": execution_id},
    )
    return LaunchedRun(execution_id=execution_id)
