from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.dependencies import get_auditor, get_job_launcher
from admin.server.jobs import JobLauncher, group_for_execution, job_name
from library.application.ports.logs import ILogReader
from library.providers.registry import get_cloud_provider

router = APIRouter(prefix="/runs", tags=["Runs"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]
LauncherDependency = Annotated[JobLauncher, Depends(get_job_launcher)]


def get_log_reader() -> ILogReader:
    return get_cloud_provider().log_reader()


LogReaderDependency = Annotated[ILogReader, Depends(get_log_reader)]


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
            create_time=execution.created_at,
            start_time=execution.started_at,
            completion_time=execution.completed_at,
            task_count=execution.task_count,
            succeeded_count=execution.succeeded_count,
            failed_count=execution.failed_count,
            args=execution.args,
        )


@router.get("/{execution_id}/logs")
async def get_run_logs(
    execution_id: str,
    launcher: LauncherDependency,
    log_reader: LogReaderDependency,
    auditor: AuditorDependency,
) -> RunLogs:
    async with auditor.operation(operation="runs.logs", organization_id=None, parameters={}):
        await launcher.execution(execution_id=execution_id)
        lines = await log_reader.read_execution_logs(
            job_name=job_name(group_for_execution(execution_id)), execution_id=execution_id
        )
        return RunLogs(
            execution_id=execution_id,
            lines=[
                RunLogLine(timestamp=line.timestamp, severity=line.severity, message=line.message) for line in lines
            ],
        )
