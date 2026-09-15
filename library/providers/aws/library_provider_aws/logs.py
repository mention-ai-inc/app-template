from datetime import UTC, datetime
from typing import Any, cast

from botocore.exceptions import ClientError

from library.application.ports.jobs import IJobRunner
from library.application.ports.logs import DEFAULT_LOG_LINE_LIMIT, LogLine
from library_provider_aws.clients import JOB_CONTAINER_NAME, client, error_code
from library_provider_aws.jobs import task_id_from

MISSING_LOG_GROUP_CODES = frozenset({"ResourceNotFoundException"})
PAGE_SIZE = 1000


def log_group_for(job_name: str, /) -> str:
    return f"/ecs/{job_name}"


def log_stream_for(task_id: str, /) -> str:
    return f"{JOB_CONTAINER_NAME}/{JOB_CONTAINER_NAME}/{task_id}"


class CloudWatchLogReader:
    def __init__(self, *, job_runner: IJobRunner) -> None:
        self._job_runner = job_runner

    async def read_execution_logs(
        self, *, job_name: str, execution_id: str, limit: int = DEFAULT_LOG_LINE_LIMIT
    ) -> list[LogLine]:
        await self._job_runner.get_execution(job_name=job_name, execution_id=execution_id)
        stream = log_stream_for(task_id_from(execution_id, job_name=job_name))

        collected: list[LogLine] = []
        next_token: str | None = None
        async with client("logs") as logs:
            while len(collected) < limit:
                keywords: dict[str, Any] = {
                    "logGroupName": log_group_for(job_name),
                    "logStreamNamePrefix": stream,
                    "limit": min(PAGE_SIZE, limit - len(collected)),
                }
                if next_token is not None:
                    keywords["nextToken"] = next_token

                try:
                    response = await logs.filter_log_events(**keywords)
                except ClientError as error:
                    if error_code(error) in MISSING_LOG_GROUP_CODES:
                        return collected
                    raise

                collected.extend(
                    _as_log_line(event) for event in cast(list[dict[str, Any]], response.get("events", []))
                )
                next_token = response.get("nextToken")
                if not next_token:
                    break

        return collected[:limit]


def _as_log_line(event: dict[str, Any], /) -> LogLine:
    return LogLine(
        timestamp=datetime.fromtimestamp(int(event.get("timestamp", 0)) / 1000, UTC),
        message=str(event.get("message", "")).rstrip("\n"),
    )
