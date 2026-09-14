from collections.abc import Callable
from typing import Any

import pytest
from tests.server.conftest import FakeAuditPublisher, FakeCloudRun, FakeUsersClient

from admin.backfill.registry import Backfill
from admin.server.routers import backfills as backfills_routes
from library.application.ports.users import Organization
from library.domain.audit.action import AuditAction
from library.domain.value_objects.users import OrganizationID

BACKFILLS = [
    Backfill(name="known-backfill", description="A test backfill.", run=lambda **kwargs: None),  # noqa: ARG005
]


@pytest.fixture(autouse=True)
def known_backfills(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backfills_routes, "discover", lambda: BACKFILLS)


async def test_list_backfills_reports_names_and_image(
    monkeypatch: pytest.MonkeyPatch, client_factory: Callable[..., Any]
) -> None:
    monkeypatch.setenv("COMMIT_SHA", "abc123")
    monkeypatch.setenv("IMAGE_DIGEST", "sha256:test")

    async with client_factory() as client:
        response = await client.get("/backfills")

    assert response.status_code == 200
    body = response.json()
    assert [backfill["name"] for backfill in body["backfills"]] == ["known-backfill"]
    assert body["job_image"] == "image@sha256:test"
    assert body["commit_sha"] == "abc123"
    assert body["image_digest"] == "sha256:test"


async def test_unknown_backfill_is_not_found(client_factory: Callable[..., Any], cloud_run: FakeCloudRun) -> None:
    async with client_factory() as client:
        response = await client.post("/backfills/unknown-backfill/runs", json={})

    assert response.status_code == 404
    assert cloud_run.launches == []


async def test_run_backfill_launches_job_with_cli_args(
    client_factory: Callable[..., Any], cloud_run: FakeCloudRun
) -> None:
    async with client_factory() as client:
        response = await client.post(
            "/backfills/known-backfill/runs",
            json={"apply": True, "organization_id": "org_1"},
        )

    assert response.status_code == 200
    assert response.json() == {"execution_id": "testadmin-j-backfill-abc12"}
    assert cloud_run.launches == [
        {
            "job_name": "testadmin-j-backfill",
            "args": ["run", "known-backfill", "--apply", "--organization-id", "org_1"],
        }
    ]


async def test_run_backfill_defaults_to_dry_run(client_factory: Callable[..., Any], cloud_run: FakeCloudRun) -> None:
    async with client_factory() as client:
        response = await client.post("/backfills/known-backfill/runs", json={})

    assert response.status_code == 200
    assert cloud_run.launches[0]["args"] == ["run", "known-backfill"]


async def test_production_run_with_apply_launches_job(
    client_factory: Callable[..., Any], cloud_run: FakeCloudRun
) -> None:
    async with client_factory(environment="") as client:
        response = await client.post("/backfills/known-backfill/runs", json={"apply": True})

    assert response.status_code == 200
    assert cloud_run.launches == [{"job_name": "admin-j-backfill", "args": ["run", "known-backfill", "--apply"]}]


async def test_scoped_run_audits_one_event_with_execution_id(
    client_factory: Callable[..., Any], publisher: FakeAuditPublisher
) -> None:
    async with client_factory() as client:
        response = await client.post("/backfills/known-backfill/runs", json={"organization_id": "org_1"})

    assert response.status_code == 200
    launch_events = [event for event in publisher.saved if event.action == AuditAction.ADMIN_OPERATION_REQUESTED]
    assert len(launch_events) == 1
    assert launch_events[0].organization_id == "org_1"
    assert launch_events[0].changes is not None
    changes = {change.field: change.after for change in launch_events[0].changes}
    assert changes["execution_id"] == "testadmin-j-backfill-abc12"
    assert changes["backfill"] == "known-backfill"


async def test_global_run_audits_one_event_per_organization(
    client_factory: Callable[..., Any],
    publisher: FakeAuditPublisher,
    users_client: FakeUsersClient,
) -> None:
    users_client.organizations = [
        Organization.model_construct(id=OrganizationID("org_1")),
        Organization.model_construct(id=OrganizationID("org_2")),
    ]

    async with client_factory() as client:
        response = await client.post("/backfills/known-backfill/runs", json={})

    assert response.status_code == 200
    launch_events = [event for event in publisher.saved if event.action == AuditAction.ADMIN_OPERATION_REQUESTED]
    assert [event.organization_id for event in launch_events] == ["org_1", "org_2"]
    for event in launch_events:
        assert event.changes is not None
        changes = {change.field: change.after for change in event.changes}
        assert changes["execution_id"] == "testadmin-j-backfill-abc12"
