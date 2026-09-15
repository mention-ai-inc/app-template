from datetime import datetime
from typing import Any, cast

import httpx

from library.application.ports.jobs import JobDefinition, JobExecution, JobStatus
from library.infrastructure.control_plane import JobExecutionNotFoundError, JobNotFoundError
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import ARM_SCOPE, JOBS_API_VERSION, arm_endpoint, job_resource_path

JOB_CONTAINER_NAME = "app"
REQUEST_TIMEOUT_SECONDS = 60
SUCCEEDED_STATUSES = frozenset({"Succeeded"})
FAILED_STATUSES = frozenset({"Failed", "Degraded", "Stopped", "Cancelled"})
RUNNING_STATUSES = frozenset({"Running", "Processing"})


class ContainerAppJobRunner:
    async def run_job(self, *, job_name: str, args: list[str]) -> str:
        body = {"template": {"containers": [{"name": JOB_CONTAINER_NAME, "args": args}]}}
        payload = await self.__request(
            "POST", f"{job_resource_path(job_name)}/start", json=body, missing=JobNotFoundError(job_name)
        )
        return _execution_name_of(payload, job_name=job_name)

    async def get_job(self, *, job_name: str) -> JobDefinition:
        payload = await self.__request("GET", job_resource_path(job_name), missing=JobNotFoundError(job_name))
        properties = cast(dict[str, Any], payload.get("properties", {}))
        template = cast(dict[str, Any], properties.get("template", {}))
        containers = cast(list[dict[str, Any]], template.get("containers", []))
        return JobDefinition(job_name=job_name, image=str(containers[0]["image"]) if containers else None)

    async def get_execution(self, *, job_name: str, execution_id: str) -> JobExecution:
        payload = await self.__request(
            "GET",
            f"{job_resource_path(job_name)}/executions/{execution_id}",
            missing=JobExecutionNotFoundError(execution_id),
        )
        return _as_job_execution(payload, execution_id=execution_id, job_name=job_name)

    async def __request(
        self, method: str, path: str, /, *, missing: Exception, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        token = await AzureClients.credential().get_token(ARM_SCOPE)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method,
                f"{arm_endpoint()}{path}",
                params={"api-version": JOBS_API_VERSION},
                headers={"Authorization": f"Bearer {token.token}"},
                json=json,
            )

        if response.status_code == 404:
            raise missing
        response.raise_for_status()
        return cast(dict[str, Any], response.json() or {})


def _execution_name_of(payload: dict[str, Any], /, *, job_name: str) -> str:
    name = payload.get("name") or cast(dict[str, Any], payload.get("properties", {})).get("name")
    if not name:
        raise JobNotFoundError(job_name)
    return str(name)


def _as_job_execution(payload: dict[str, Any], /, *, execution_id: str, job_name: str) -> JobExecution:
    properties = cast(dict[str, Any], payload.get("properties", {}))
    status = _status_of(str(properties.get("status", "")))
    return JobExecution(
        execution_id=execution_id,
        job_name=job_name,
        status=status,
        args=_args_of(properties),
        started_at=_time(properties, "startTime"),
        completed_at=_time(properties, "endTime"),
        succeeded_count=1 if status == "succeeded" else 0,
        failed_count=1 if status == "failed" else 0,
    )


def _status_of(status: str, /) -> JobStatus:
    if status in SUCCEEDED_STATUSES:
        return "succeeded"
    if status in FAILED_STATUSES:
        return "failed"
    if status in RUNNING_STATUSES:
        return "running"
    return "pending"


def _args_of(properties: dict[str, Any], /) -> list[str]:
    template = cast(dict[str, Any], properties.get("template", {}))
    for container in cast(list[dict[str, Any]], template.get("containers", [])):
        if container.get("name") == JOB_CONTAINER_NAME:
            return [str(entry) for entry in container.get("args", [])]
    return []


def _time(properties: dict[str, Any], field: str, /) -> datetime | None:
    value = properties.get(field)
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
