from collections.abc import Callable
from typing import Any

import pytest
from tests.server.conftest import LIST_ARGS, FakeAuditPublisher, FakeUsersClient, launches, run_launches

from control_plane.application.ports.users import Organization
from control_plane.domain.audit.action import AuditAction
from control_plane.domain.value_objects.users import OrganizationID
from control_plane.providers.local.jobs import LocalJobRunner


async def test_list_backfills_reports_the_deployed_catalogue_and_image(
    monkeypatch: pytest.MonkeyPatch, client_factory: Callable[..., Any], job_runner: LocalJobRunner
) -> None:
    monkeypatch.setenv("COMMIT_SHA", "abc123")
    monkeypatch.setenv("IMAGE_DIGEST", "sha256:test")

    async with client_factory() as client:
        response = await client.get("/backfills")

    assert response.status_code == 200
    body = response.json()
    assert body["backfills"] == [{"name": "known-backfill", "description": "A test backfill."}]
    assert body["job_image"] == "image@sha256:test"
    assert body["commit_sha"] == "abc123"
    assert body["image_digest"] == "sha256:test"
    assert launches(job_runner) == [{"job_name": "testadmin-j-backfill", "args": LIST_ARGS}]


async def test_listing_twice_asks_the_job_once(client_factory: Callable[..., Any], job_runner: LocalJobRunner) -> None:
    async with client_factory() as client:
        first = await client.get("/backfills")
        second = await client.get("/backfills")

    assert first.json()["backfills"] == second.json()["backfills"]
    assert len(launches(job_runner)) == 1


async def test_unknown_backfill_is_not_found(client_factory: Callable[..., Any], job_runner: LocalJobRunner) -> None:
    async with client_factory() as client:
        response = await client.post("/backfills/unknown-backfill/runs", json={})

    assert response.status_code == 404
    assert run_launches(job_runner) == []


async def test_run_backfill_launches_job_with_cli_args(
    client_factory: Callable[..., Any], job_runner: LocalJobRunner
) -> None:
    async with client_factory() as client:
        response = await client.post(
            "/backfills/known-backfill/runs",
            json={"apply": True, "organization_id": "org_1"},
        )

    assert response.status_code == 200
    assert response.json()["execution_id"].startswith("testadmin-j-backfill-")
    assert run_launches(job_runner) == [
        {
            "job_name": "testadmin-j-backfill",
            "args": ["run", "known-backfill", "--apply", "--organization-id", "org_1"],
        }
    ]


async def test_run_backfill_defaults_to_dry_run(client_factory: Callable[..., Any], job_runner: LocalJobRunner) -> None:
    async with client_factory() as client:
        response = await client.post("/backfills/known-backfill/runs", json={})

    assert response.status_code == 200
    assert run_launches(job_runner)[0]["args"] == ["run", "known-backfill"]


async def test_production_run_with_apply_launches_job(
    client_factory: Callable[..., Any], job_runner: LocalJobRunner
) -> None:
    async with client_factory(environment="") as client:
        response = await client.post("/backfills/known-backfill/runs", json={"apply": True})

    assert response.status_code == 200
    assert run_launches(job_runner) == [{"job_name": "admin-j-backfill", "args": ["run", "known-backfill", "--apply"]}]


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
    assert str(changes["execution_id"]).startswith("testadmin-j-backfill-")
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
        assert str(changes["execution_id"]).startswith("testadmin-j-backfill-")
