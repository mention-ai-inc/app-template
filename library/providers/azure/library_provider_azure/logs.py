from datetime import datetime
from typing import Any, cast

import httpx

from library.application.ports.jobs import IJobRunner
from library.application.ports.logs import DEFAULT_LOG_LINE_LIMIT, LogLine
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import (
    LOG_ANALYTICS_ENDPOINT,
    LOG_ANALYTICS_SCOPE,
    LOG_ANALYTICS_WORKSPACE_ID,
    required,
)

CONSOLE_LOGS_TABLE = "ContainerAppConsoleLogs_CL"
REQUEST_TIMEOUT_SECONDS = 60


class LogAnalyticsReader:
    def __init__(self, *, job_runner: IJobRunner) -> None:
        self._job_runner = job_runner

    async def read_execution_logs(
        self, *, job_name: str, execution_id: str, limit: int = DEFAULT_LOG_LINE_LIMIT
    ) -> list[LogLine]:
        await self._job_runner.get_execution(job_name=job_name, execution_id=execution_id)

        token = await AzureClients.credential().get_token(LOG_ANALYTICS_SCOPE)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{LOG_ANALYTICS_ENDPOINT}/v1/workspaces/{required(LOG_ANALYTICS_WORKSPACE_ID)}/query",
                headers={"Authorization": f"Bearer {token.token}"},
                json={"query": _query_for(execution_id, limit=limit)},
            )
        response.raise_for_status()
        return _as_log_lines(cast(dict[str, Any], response.json()))


def _query_for(execution_id: str, /, *, limit: int) -> str:
    return (
        f"{CONSOLE_LOGS_TABLE}"
        f" | where ContainerGroupName_s startswith '{execution_id}'"
        " | project TimeGenerated, Log_s"
        " | order by TimeGenerated asc"
        f" | limit {limit}"
    )


def _as_log_lines(payload: dict[str, Any], /) -> list[LogLine]:
    tables = cast(list[dict[str, Any]], payload.get("tables", []))
    if not tables:
        return []

    columns = [str(column["name"]) for column in cast(list[dict[str, Any]], tables[0].get("columns", []))]
    rows = cast(list[list[Any]], tables[0].get("rows", []))
    timestamp_at = columns.index("TimeGenerated")
    message_at = columns.index("Log_s")

    return [
        LogLine(
            timestamp=datetime.fromisoformat(str(row[timestamp_at]).replace("Z", "+00:00")),
            message=str(row[message_at] or ""),
        )
        for row in rows
    ]
