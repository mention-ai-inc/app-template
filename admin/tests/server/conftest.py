import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from admin.server.app import create_admin_app
from admin.server.audit import AdminAuditor
from admin.server.auth import Operator, require_operator
from admin.server.dependencies import get_auditor, get_job_launcher
from admin.server.jobs import JobLauncher
from admin.server.routers import runs as runs_routes
from library.application.ports.users import Organization
from library.domain.audit.action import AuditAction
from library.domain.audit.change import FieldChange
from library.domain.audit.event import AuditEventID
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.audit.publisher import AuditEventPublisher
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.dependencies import get_users_client
from library.providers.local.jobs import LocalJobRunner, LocalLogReader

STAFF_EMAIL = "engineer@acme.example.com"
JOB_IMAGE = "image@sha256:test"
JOB_LOG_LINE = "Working..."
JOB_NAMES = ("testadmin-j-backfill", "testadmin-j-seed", "admin-j-backfill", "admin-j-seed")

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


async def _job(args: list[str]) -> None:  # noqa: ARG001
    logger.info(JOB_LOG_LINE)


def launches(job_runner: LocalJobRunner) -> list[dict[str, Any]]:
    return [{"job_name": execution.job_name, "args": execution.args} for execution in job_runner.executions.values()]


async def run_to_completion(job_runner: LocalJobRunner, *, job_name: str, args: list[str]) -> str:
    execution_id = await job_runner.run_job(job_name=job_name, args=args)
    while job_runner.executions[execution_id].status not in ("succeeded", "failed"):
        await asyncio.sleep(0)
    return execution_id


class FakeUsersClient:
    def __init__(self) -> None:
        self.organizations: list[Organization] = []

    async def list_organizations(self) -> list[Organization]:
        return self.organizations


class RecordedAuditEvent(BaseModel):
    action: AuditAction
    resource_type: str
    resource_id: str
    organization_id: OrganizationID | None
    changes: list[FieldChange] | None


class FakeAuditPublisher(AuditEventPublisher):
    def __init__(self) -> None:
        self.saved: list[RecordedAuditEvent] = []

    async def quick_save(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        organization_id: OrganizationID | None,
        changes: list[FieldChange] | None,
    ) -> AuditEventID:
        self.saved.append(
            RecordedAuditEvent(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                organization_id=organization_id,
                changes=changes,
            )
        )
        return AuditEventID()


@pytest.fixture
def publisher() -> FakeAuditPublisher:
    return FakeAuditPublisher()


@pytest.fixture
def job_runner() -> LocalJobRunner:
    runner = LocalJobRunner()
    for name in JOB_NAMES:
        runner.register(job_name=name, handler=_job, image=JOB_IMAGE)
    return runner


@pytest.fixture
def users_client() -> FakeUsersClient:
    return FakeUsersClient()


@pytest.fixture
def build_app(
    monkeypatch: pytest.MonkeyPatch,
    publisher: FakeAuditPublisher,
    job_runner: LocalJobRunner,
    users_client: FakeUsersClient,
) -> Callable[..., FastAPI]:
    def build(*, environment: str = "test") -> FastAPI:
        monkeypatch.setenv("FEATURE_ENVIRONMENT", environment)
        monkeypatch.setenv("SERVICE", "admin")
        monkeypatch.setenv("COMPONENT_TYPE", "server")
        monkeypatch.setenv("COMPONENT_NAME", "rest")
        app = create_admin_app()
        app.dependency_overrides[require_operator] = lambda: Operator(subject="operator:12345", email=STAFF_EMAIL)
        app.dependency_overrides[get_auditor] = lambda: AdminAuditor(publisher=publisher)
        app.dependency_overrides[get_job_launcher] = lambda: JobLauncher(job_runner=job_runner)
        app.dependency_overrides[runs_routes.get_log_reader] = lambda: LocalLogReader(runner=job_runner)
        app.dependency_overrides[get_users_client] = lambda: users_client
        return app

    return build


@pytest.fixture
def client_factory(build_app: Callable[..., FastAPI]) -> Callable[..., Any]:
    @asynccontextmanager
    async def factory(*, environment: str = "test") -> AsyncGenerator[AsyncClient]:
        transport = ASGITransport(app=build_app(environment=environment))
        async with AsyncClient(transport=transport, base_url="http://admin.test") as client:
            yield client

    return factory
