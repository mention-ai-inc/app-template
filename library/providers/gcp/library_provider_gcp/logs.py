from library.application.ports.jobs import IJobRunner
from library.application.ports.logs import DEFAULT_LOG_LINE_LIMIT, LogLine
from library_provider_gcp.cloud.logging import CloudLogging
from library_provider_gcp.cloud.project import get_project_id

EXECUTION_RESOURCE_TYPE = "cloud_run_job"
EXECUTION_NAME_LABEL = "run.googleapis.com/execution_name"


class CloudLoggingReader:
    def __init__(self, *, job_runner: IJobRunner, cloud_logging: CloudLogging | None = None) -> None:
        self._job_runner = job_runner
        self._cloud_logging = cloud_logging or CloudLogging()

    async def read_execution_logs(
        self, *, job_name: str, execution_id: str, limit: int = DEFAULT_LOG_LINE_LIMIT
    ) -> list[LogLine]:
        await self._job_runner.get_execution(job_name=job_name, execution_id=execution_id)
        entries = await self._cloud_logging.list_entries(
            project=get_project_id(),
            log_filter=(
                f'resource.type="{EXECUTION_RESOURCE_TYPE}" AND labels."{EXECUTION_NAME_LABEL}"="{execution_id}"'
            ),
            limit=limit,
        )
        return [LogLine(timestamp=entry.timestamp, message=entry.message, severity=entry.severity) for entry in entries]
