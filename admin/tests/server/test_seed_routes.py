from collections.abc import Callable
from typing import Any

from tests.server.conftest import FakeAuditPublisher, launches

from library.domain.audit.action import AuditAction
from library.providers.local.jobs import LocalJobRunner


async def test_seed_run_launches_job_with_cli_args(
    client_factory: Callable[..., Any], job_runner: LocalJobRunner
) -> None:
    async with client_factory() as client:
        response = await client.post("/seed/runs", json={"organization_id": "org_seed"})

    assert response.status_code == 200
    assert response.json()["execution_id"].startswith("testadmin-j-seed-")
    assert launches(job_runner) == [{"job_name": "testadmin-j-seed", "args": ["run", "--organization-id", "org_seed"]}]


async def test_seed_run_without_organization_lets_the_job_create_one(
    client_factory: Callable[..., Any], job_runner: LocalJobRunner, publisher: FakeAuditPublisher
) -> None:
    async with client_factory() as client:
        response = await client.post("/seed/runs", json={})

    assert response.status_code == 200
    assert launches(job_runner)[0]["args"] == ["run"]
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
    changes = {change.field: change.after for change in events[0].changes}
    assert set(changes) == {"execution_id"}
    assert str(changes["execution_id"]).startswith("testadmin-j-seed-")
