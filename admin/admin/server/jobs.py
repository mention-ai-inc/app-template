from httpx import HTTPStatusError

from admin.common.environment import feature_environment
from library.application.errors import ApplicationError, ApplicationErrorType
from library.infrastructure.cloud.run import CloudRun, Execution

JOB_GROUPS = ("backfill", "seed")


def job_name(group: str) -> str:
    return f"{feature_environment()}admin-j-{group}"


def group_for_execution(execution_id: str) -> str:
    for group in JOB_GROUPS:
        if execution_id.startswith(f"{job_name(group)}-"):
            return group
    raise ApplicationError(
        error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
        message=f"Unknown execution: {execution_id}.",
    )


class JobLauncher:
    def __init__(self, *, cloud_run: CloudRun) -> None:
        self._cloud_run = cloud_run

    async def launch(self, *, group: str, args: list[str]) -> str:
        return await self._cloud_run.run_job(job_name=job_name(group), args=args)

    async def execution(self, *, execution_id: str) -> Execution:
        group = group_for_execution(execution_id)
        try:
            return await self._cloud_run.get_execution(job_name=job_name(group), execution_name=execution_id)
        except HTTPStatusError as error:
            if error.response.status_code == 404:
                raise ApplicationError(
                    error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                    message=f"Execution {execution_id} not found.",
                ) from error
            raise

    async def job_image(self, *, group: str) -> str | None:
        return (await self._cloud_run.get_job(job_name=job_name(group))).image
