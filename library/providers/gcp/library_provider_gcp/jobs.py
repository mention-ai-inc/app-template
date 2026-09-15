from typing import cast

from httpx import HTTPStatusError

from library.application.ports.jobs import JobDefinition, JobExecution, JobStatus
from library.infrastructure.control_plane import JobExecutionNotFoundError, JobNotFoundError
from library_provider_gcp.cloud.run import CloudRun, Execution


class CloudRunJobRunner:
    def __init__(self, *, cloud_run: CloudRun | None = None) -> None:
        self._cloud_run = cloud_run or CloudRun()

    async def run_job(self, *, job_name: str, args: list[str]) -> str:
        return await self._cloud_run.run_job(job_name=job_name, args=args)

    async def get_job(self, *, job_name: str) -> JobDefinition:
        try:
            job = await self._cloud_run.get_job(job_name=job_name)
        except HTTPStatusError as error:
            if error.response.status_code == 404:
                raise JobNotFoundError(job_name) from error
            raise
        return JobDefinition(job_name=job_name, image=job.image)

    async def get_execution(self, *, job_name: str, execution_id: str) -> JobExecution:
        try:
            execution = await self._cloud_run.get_execution(job_name=job_name, execution_name=execution_id)
        except HTTPStatusError as error:
            if error.response.status_code == 404:
                raise JobExecutionNotFoundError(execution_id) from error
            raise
        return _as_job_execution(execution, job_name=job_name)


def _as_job_execution(execution: Execution, /, *, job_name: str) -> JobExecution:
    return JobExecution(
        execution_id=execution.short_name,
        job_name=job_name,
        status=cast(JobStatus, execution.status),
        args=execution.args,
        created_at=execution.create_time,
        started_at=execution.start_time,
        completed_at=execution.completion_time,
        task_count=execution.task_count,
        succeeded_count=execution.succeeded_count,
        failed_count=execution.failed_count + execution.cancelled_count,
    )
