"""Launching admin jobs from a laptop or CI.

The deployed admin API is for people: whichever gate fronts it — IAP, ALB OIDC, Entra — terminates a
browser login, and none of them admits a machine. So the CLI does not call the API at all. It
resolves the same `IJobRunner` and `ILogReader` the server uses, launches the job with the operator's
own cloud credentials, and follows the execution to a terminal status.

Inside the job container the commands take the other branch entirely and run their worker in process;
`runs_in_job` is what tells them apart, from the `COMPONENT_TYPE` every job module injects.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from admin.client.local_jobs import register_local_jobs
from admin.server.audit import AdminAuditor
from admin.server.jobs import JobLauncher, job_name
from library.application.audit.context import set_actor, set_source
from library.application.ports.jobs import JobExecution
from library.domain.audit.actor import AuditActor, AuditActorType
from library.domain.audit.event import AuditSource
from library.infrastructure.audit.publisher import AuditEventPublisher
from library.presentation.api.environment import ComponentType
from library.presentation.dependencies import get_users_client
from library.providers.registry import get_cloud_provider

POLL_INTERVAL_SECONDS = 2
TERMINAL_STATUSES = ("succeeded", "failed")
ADMIN_SERVICE = "admin"


def runs_in_job() -> bool:
    return os.getenv("COMPONENT_TYPE", "") == ComponentType.JOB


async def launch_and_follow(
    *, group: str, operation: str, args: list[str], organization_id: str | None, parameters: dict[str, Any]
) -> JobExecution:
    launcher = _launcher()
    execution_id = await launcher.launch(group=group, args=args)
    print(f"Execution: {execution_id}")

    await _record_launch(
        operation=operation,
        organization_id=organization_id,
        parameters={**parameters, "execution_id": execution_id},
    )

    execution = await _follow(launcher, execution_id=execution_id)
    await _print_logs(group=group, execution_id=execution_id)
    if execution.status != "succeeded":
        raise SystemExit(1)
    return execution


async def deployed_job_image(*, group: str) -> str | None:
    return await _launcher().job_image(group=group)


def _launcher() -> JobLauncher:
    register_local_jobs()
    return JobLauncher(job_runner=get_cloud_provider().job_runner())


async def _follow(launcher: JobLauncher, *, execution_id: str) -> JobExecution:
    last_status = ""
    while True:
        execution = await launcher.execution(execution_id=execution_id)
        if execution.status != last_status:
            last_status = execution.status
            print(f"  {last_status}")
        if execution.status in TERMINAL_STATUSES:
            return execution
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _print_logs(*, group: str, execution_id: str) -> None:
    lines = (
        await get_cloud_provider().log_reader().read_execution_logs(job_name=job_name(group), execution_id=execution_id)
    )
    for line in lines:
        print(f"  {line.message}")


async def _record_launch(*, operation: str, organization_id: str | None, parameters: dict[str, Any]) -> None:
    identity = await get_cloud_provider().operator_auth().caller_identity()
    set_actor(
        AuditActor(
            actor_type=AuditActorType.OPERATOR,
            actor_id=identity,
            actor_email=identity if "@" in identity else None,
            actor_role=None,
            impersonated_by=None,
        )
    )
    set_source(AuditSource.JOB)
    await AdminAuditor(publisher=AuditEventPublisher(service=ADMIN_SERVICE)).launch_requested(
        operation=operation,
        organization_id=organization_id,
        parameters=parameters,
        users_client=get_users_client(),
    )
