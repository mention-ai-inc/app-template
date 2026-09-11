from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, HTTPStatusError, Request, Response
from pydantic import BaseModel

from admin.server.app import create_admin_app
from admin.server.audit import AdminAuditor
from admin.server.auth import Operator, require_operator
from admin.server.dependencies import get_auditor, get_job_launcher
from admin.server.jobs import JobLauncher
from library.application.users import Organization
from library.domain.audit.action import AuditAction
from library.domain.audit.change import FieldChange
from library.domain.audit.event import AuditEventID
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.audit.publisher import AuditEventPublisher
from library.infrastructure.cloud.run import CloudRun, Execution, Job
from library.presentation.dependencies import get_users_client

STAFF_EMAIL = "engineer@acme.example.com"


class FakeCloudRun(CloudRun):
    def __init__(self) -> None:
        super().__init__(project="test-project")
        self.launches: list[dict[str, Any]] = []
        self.executions: dict[str, Execution] = {}
        self.jobs: dict[str, Job] = {}

    async def run_job(self, *, job_name: str, args: list[str]) -> str:
        self.launches.append({"job_name": job_name, "args": args})
        return f"{job_name}-abc12"

    async def get_job(self, *, job_name: str) -> Job:
        if job_name in self.jobs:
            return self.jobs[job_name]
        return Job.model_validate(
            {"name": job_name, "template": {"template": {"containers": [{"image": "image@sha256:test"}]}}}
        )

    async def get_execution(self, *, job_name: str, execution_name: str) -> Execution:
        if execution_name not in self.executions:
            request = Request("GET", f"https://run.googleapis.com/{job_name}/executions/{execution_name}")
            raise HTTPStatusError("not found", request=request, response=Response(404, request=request))
        return self.executions[execution_name]


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
def cloud_run() -> FakeCloudRun:
    return FakeCloudRun()


@pytest.fixture
def users_client() -> FakeUsersClient:
    return FakeUsersClient()


@pytest.fixture
def build_app(
    monkeypatch: pytest.MonkeyPatch,
    publisher: FakeAuditPublisher,
    cloud_run: FakeCloudRun,
    users_client: FakeUsersClient,
) -> Callable[..., FastAPI]:
    def build(*, environment: str = "test") -> FastAPI:
        monkeypatch.setenv("FEATURE_ENVIRONMENT", environment)
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
        monkeypatch.setenv("SERVICE", "admin")
        monkeypatch.setenv("COMPONENT_TYPE", "server")
        monkeypatch.setenv("COMPONENT_NAME", "rest")
        app = create_admin_app()
        app.dependency_overrides[require_operator] = lambda: Operator(
            subject="accounts.google.com:12345", email=STAFF_EMAIL
        )
        app.dependency_overrides[get_auditor] = lambda: AdminAuditor(publisher=publisher)
        app.dependency_overrides[get_job_launcher] = lambda: JobLauncher(cloud_run=cloud_run)
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
