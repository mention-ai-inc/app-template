from collections.abc import Callable
from typing import Any

from httpx import ASGITransport, AsyncClient
from tests.server.conftest import FakeCloudRun

from admin.server.routers import runs as runs_routes
from library.infrastructure.cloud.logging import CloudLogging, LogEntry
from library.infrastructure.cloud.run import Execution

EXECUTION_ID = "testadmin-j-backfill-abc12"


def _seed_execution(cloud_run: FakeCloudRun) -> None:
    cloud_run.executions[EXECUTION_ID] = Execution.model_validate(
        {
            "name": f"projects/p/locations/l/jobs/testadmin-j-backfill/executions/{EXECUTION_ID}",
            "createTime": "2026-07-26T10:00:00Z",
            "startTime": "2026-07-26T10:00:05Z",
            "completionTime": "2026-07-26T10:01:00Z",
            "taskCount": 1,
            "succeededCount": 1,
            "template": {"containers": [{"image": "image@sha256:test", "args": ["run", "known-backfill"]}]},
        }
    )


class FakeCloudLogging(CloudLogging):
    def __init__(self) -> None:
        super().__init__()
        self.filters: list[str] = []

    async def list_entries(
        self,
        *,
        project: str,  # noqa: ARG002
        log_filter: str,
        page_size: int = 1000,  # noqa: ARG002
    ) -> list[LogEntry]:
        self.filters.append(log_filter)
        return [
            LogEntry.model_validate(
                {"timestamp": "2026-07-26T10:00:10Z", "severity": "INFO", "textPayload": "Working..."}
            )
        ]


async def test_get_run_reports_execution_status(client_factory: Callable[..., Any], cloud_run: FakeCloudRun) -> None:
    _seed_execution(cloud_run)

    async with client_factory() as client:
        response = await client.get(f"/runs/{EXECUTION_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] == EXECUTION_ID
    assert body["group"] == "backfill"
    assert body["status"] == "succeeded"
    assert body["args"] == ["run", "known-backfill"]


async def test_get_run_for_missing_execution_is_not_found(client_factory: Callable[..., Any]) -> None:
    async with client_factory() as client:
        response = await client.get(f"/runs/{EXECUTION_ID}")

    assert response.status_code == 404


async def test_get_run_logs_filters_by_execution(cloud_run: FakeCloudRun, build_app: Callable[..., Any]) -> None:
    _seed_execution(cloud_run)
    fake_logging = FakeCloudLogging()
    app = build_app()
    app.dependency_overrides[runs_routes.get_cloud_logging] = lambda: fake_logging

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://admin.test") as client:
        response = await client.get(f"/runs/{EXECUTION_ID}/logs")

    assert response.status_code == 200
    body = response.json()
    assert body["lines"] == [{"timestamp": "2026-07-26T10:00:10Z", "severity": "INFO", "message": "Working..."}]
    assert len(fake_logging.filters) == 1
    assert EXECUTION_ID in fake_logging.filters[0]
