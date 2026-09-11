from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.dependencies import get_auditor, get_job_launcher
from admin.server.jobs import JobLauncher, group_for_execution
from library.infrastructure.cloud.logging import CloudLogging
from library.infrastructure.cloud.project import get_project_id

router = APIRouter(prefix="/runs", tags=["Runs"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]
LauncherDependency = Annotated[JobLauncher, Depends(get_job_launcher)]


def get_cloud_logging() -> CloudLogging:
    return CloudLogging()


LoggingDependency = Annotated[CloudLogging, Depends(get_cloud_logging)]


class RunStatus(BaseModel):
    execution_id: str
    group: str
    status: str
    create_time: datetime | None
    start_time: datetime | None
    completion_time: datetime | None
    task_count: int
    succeeded_count: int
    failed_count: int
    args: list[str]


class RunLogLine(BaseModel):
    timestamp: datetime
    severity: str | None
    message: str


class RunLogs(BaseModel):
    execution_id: str
    lines: list[RunLogLine]


@router.get("/{execution_id}")
async def get_run(execution_id: str, launcher: LauncherDependency, auditor: AuditorDependency) -> RunStatus:
    async with auditor.operation(operation="runs.show", organization_id=None, parameters={}):
        execution = await launcher.execution(execution_id=execution_id)
        return RunStatus(
            execution_id=execution_id,
            group=group_for_execution(execution_id),
            status=execution.status,
            create_time=execution.create_time,
            start_time=execution.start_time,
            completion_time=execution.completion_time,
            task_count=execution.task_count,
            succeeded_count=execution.succeeded_count,
            failed_count=execution.failed_count,
            args=execution.args,
        )


@router.get("/{execution_id}/logs")
async def get_run_logs(
    execution_id: str,
    launcher: LauncherDependency,
    cloud_logging: LoggingDependency,
    auditor: AuditorDependency,
) -> RunLogs:
    async with auditor.operation(operation="runs.logs", organization_id=None, parameters={}):
        await launcher.execution(execution_id=execution_id)
        entries = await cloud_logging.list_entries(
            project=get_project_id(),
            log_filter=(
                f'resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="{execution_id}"'
            ),
        )
        return RunLogs(
            execution_id=execution_id,
            lines=[
                RunLogLine(timestamp=entry.timestamp, severity=entry.severity, message=entry.message)
                for entry in entries
            ],
        )
