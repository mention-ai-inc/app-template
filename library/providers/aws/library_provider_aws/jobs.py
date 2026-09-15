from datetime import datetime
from typing import Any, cast

from botocore.exceptions import ClientError

from library.application.ports.jobs import JobDefinition, JobExecution, JobStatus
from library.infrastructure.control_plane import JobExecutionNotFoundError, JobNotFoundError
from library_provider_aws.clients import (
    JOB_CONTAINER_NAME,
    client,
    error_code,
    get_cluster_arn,
    get_job_security_group_ids,
    get_job_subnet_ids,
)

MISSING_DEFINITION_CODES = frozenset({"ClientException", "ResourceNotFoundException", "InvalidParameterException"})
PENDING_TASK_STATUSES = frozenset({"PROVISIONING", "PENDING"})
STOPPED_TASK_STATUS = "STOPPED"


class EcsJobRunner:
    async def run_job(self, *, job_name: str, args: list[str]) -> str:
        async with client("ecs") as ecs:
            response = await ecs.run_task(
                cluster=get_cluster_arn(),
                taskDefinition=job_name,
                launchType="FARGATE",
                count=1,
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": get_job_subnet_ids(),
                        "securityGroups": get_job_security_group_ids(),
                        "assignPublicIp": "DISABLED",
                    }
                },
                overrides={"containerOverrides": [{"name": JOB_CONTAINER_NAME, "command": args}]},
            )

        tasks = cast(list[dict[str, Any]], response.get("tasks", []))
        if not tasks:
            raise JobNotFoundError(job_name)
        return f"{job_name}-{task_id_of(str(tasks[0]['taskArn']))}"

    async def get_job(self, *, job_name: str) -> JobDefinition:
        async with client("ecs") as ecs:
            try:
                response = await ecs.describe_task_definition(taskDefinition=job_name)
            except ClientError as error:
                if error_code(error) in MISSING_DEFINITION_CODES:
                    raise JobNotFoundError(job_name) from error
                raise

        definition = cast(dict[str, Any], response["taskDefinition"])
        containers = cast(list[dict[str, Any]], definition.get("containerDefinitions", []))
        return JobDefinition(job_name=job_name, image=str(containers[0]["image"]) if containers else None)

    async def get_execution(self, *, job_name: str, execution_id: str) -> JobExecution:
        async with client("ecs") as ecs:
            response = await ecs.describe_tasks(
                cluster=get_cluster_arn(), tasks=[task_id_from(execution_id, job_name=job_name)]
            )

        tasks = cast(list[dict[str, Any]], response.get("tasks", []))
        if not tasks:
            raise JobExecutionNotFoundError(execution_id)
        return _as_job_execution(tasks[0], execution_id=execution_id, job_name=job_name)


def task_id_of(task_arn: str, /) -> str:
    return task_arn.rsplit("/", 1)[-1]


def task_id_from(execution_id: str, /, *, job_name: str) -> str:
    prefix = f"{job_name}-"
    if not execution_id.startswith(prefix):
        raise JobExecutionNotFoundError(execution_id)
    return execution_id[len(prefix) :]


def _as_job_execution(task: dict[str, Any], /, *, execution_id: str, job_name: str) -> JobExecution:
    status = _status_of(task)
    return JobExecution(
        execution_id=execution_id,
        job_name=job_name,
        status=status,
        args=_args_of(task),
        created_at=_time(task, "createdAt"),
        started_at=_time(task, "startedAt"),
        completed_at=_time(task, "stoppedAt"),
        succeeded_count=1 if status == "succeeded" else 0,
        failed_count=1 if status == "failed" else 0,
    )


def _status_of(task: dict[str, Any], /) -> JobStatus:
    last_status = str(task.get("lastStatus", ""))
    if last_status in PENDING_TASK_STATUSES:
        return "pending"
    if last_status != STOPPED_TASK_STATUS:
        return "running"

    containers = cast(list[dict[str, Any]], task.get("containers", []))
    exit_codes = [container.get("exitCode") for container in containers]
    if any(code is None or int(code) != 0 for code in exit_codes):
        return "failed"
    return "succeeded"


def _args_of(task: dict[str, Any], /) -> list[str]:
    overrides = cast(dict[str, Any], task.get("overrides", {}))
    containers = cast(list[dict[str, Any]], overrides.get("containerOverrides", []))
    for container in containers:
        if container.get("name") == JOB_CONTAINER_NAME:
            return [str(entry) for entry in container.get("command", [])]
    return []


def _time(task: dict[str, Any], field: str, /) -> datetime | None:
    value = task.get(field)
    return value if isinstance(value, datetime) else None
