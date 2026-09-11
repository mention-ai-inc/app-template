from collections.abc import Callable
from typing import Any

from tests.server.conftest import FakeAuditPublisher, FakeCloudRun

from library.domain.audit.action import AuditAction


async def test_seed_run_launches_job_with_cli_args(client_factory: Callable[..., Any], cloud_run: FakeCloudRun) -> None:
    async with client_factory() as client:
        response = await client.post("/seed/runs", json={"organization_id": "org_seed"})

    assert response.status_code == 200
    assert response.json() == {"execution_id": "testadmin-j-seed-abc12"}
    assert cloud_run.launches == [{"job_name": "testadmin-j-seed", "args": ["run", "--organization-id", "org_seed"]}]


async def test_seed_run_without_organization_lets_the_job_create_one(
    client_factory: Callable[..., Any], cloud_run: FakeCloudRun, publisher: FakeAuditPublisher
) -> None:
    async with client_factory() as client:
        response = await client.post("/seed/runs", json={})

    assert response.status_code == 200
    assert cloud_run.launches[0]["args"] == ["run"]
    events = [event for event in publisher.saved if event.action == AuditAction.ADMIN_OPERATION_REQUESTED]
    assert [event.organization_id for event in events] == [None]


async def test_seed_run_audits_the_target_organization(
    client_factory: Callable[..., Any], publisher: FakeAuditPublisher
) -> None:
    async with client_factory() as client:
        await client.post("/seed/runs", json={"organization_id": "org_seed"})

    events = [event for event in publisher.saved if event.action == AuditAction.ADMIN_OPERATION_REQUESTED]
    assert [event.organization_id for event in events] == ["org_seed"]
    assert events[0].changes is not None
    assert {change.field: change.after for change in events[0].changes} == {"execution_id": "testadmin-j-seed-abc12"}
