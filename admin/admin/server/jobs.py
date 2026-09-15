from admin.common.environment import feature_environment
from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.jobs import IJobRunner, JobExecution
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType

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
    def __init__(self, *, job_runner: IJobRunner) -> None:
        self._job_runner = job_runner

    async def launch(self, *, group: str, args: list[str]) -> str:
        return await self._job_runner.run_job(job_name=job_name(group), args=args)

    async def execution(self, *, execution_id: str) -> JobExecution:
        group = group_for_execution(execution_id)
        try:
            return await self._job_runner.get_execution(job_name=job_name(group), execution_id=execution_id)
        except InfrastructureError as error:
            if error.error_type == InfrastructureErrorType.NOT_FOUND_ERROR:
                raise ApplicationError(
                    error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                    message=f"Execution {execution_id} not found.",
                ) from error
            raise

    async def job_image(self, *, group: str) -> str | None:
        try:
            return (await self._job_runner.get_job(job_name=job_name(group))).image
        except InfrastructureError as error:
            if error.error_type == InfrastructureErrorType.NOT_FOUND_ERROR:
                return None
            raise
