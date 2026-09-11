from typing import Any

import pytest
from httpx import Request, Response

from library.infrastructure.cloud.base import AuthenticatedClient
from library.infrastructure.cloud.run import CloudRun

EXECUTION_NAME = "projects/p/locations/us-central1/jobs/testadmin-j-backfill/executions/testadmin-j-backfill-abc12"


async def test_run_job_overrides_args_and_never_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_post(self: AuthenticatedClient, url: str, *, json: dict[str, Any]) -> Response:  # noqa: ARG001
        captured["url"] = url
        captured["json"] = json
        return Response(
            200,
            json={"metadata": {"name": EXECUTION_NAME}},
            request=Request("POST", url),
        )

    monkeypatch.setattr(AuthenticatedClient, "post", fake_post)
    cloud_run = CloudRun(project="p")

    execution_id = await cloud_run.run_job(job_name="testadmin-j-backfill", args=["run", "some-backfill", "--apply"])

    assert execution_id == "testadmin-j-backfill-abc12"
    assert captured["url"] == "/projects/p/locations/us-central1/jobs/testadmin-j-backfill:run"
    assert captured["json"] == {"overrides": {"containerOverrides": [{"args": ["run", "some-backfill", "--apply"]}]}}


async def test_get_execution_parses_status_and_args(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: AuthenticatedClient, url: str) -> Response:  # noqa: ARG001
        return Response(
            200,
            json={
                "name": EXECUTION_NAME,
                "completionTime": "2026-07-26T10:01:00Z",
                "taskCount": 1,
                "succeededCount": 1,
                "template": {"containers": [{"image": "image@sha256:test", "args": ["run", "x"]}]},
            },
            request=Request("GET", url),
        )

    monkeypatch.setattr(AuthenticatedClient, "get", fake_get)
    cloud_run = CloudRun(project="p")

    execution = await cloud_run.get_execution(
        job_name="testadmin-j-backfill", execution_name="testadmin-j-backfill-abc12"
    )

    assert execution.short_name == "testadmin-j-backfill-abc12"
    assert execution.status == "succeeded"
    assert execution.args == ["run", "x"]
