from collections.abc import Callable
from typing import Any

from tests.server.conftest import JOB_LOG_LINE, run_to_completion

from library.providers.local.jobs import LocalJobRunner

JOB_NAME = "testadmin-j-backfill"
ARGS = ["run", "known-backfill"]
MISSING_EXECUTION_ID = "testadmin-j-backfill-missing"


async def test_get_run_reports_execution_status(client_factory: Callable[..., Any], job_runner: LocalJobRunner) -> None:
    execution_id = await run_to_completion(job_runner, job_name=JOB_NAME, args=ARGS)

    async with client_factory() as client:
        response = await client.get(f"/runs/{execution_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] == execution_id
    assert body["group"] == "backfill"
    assert body["status"] == "succeeded"
    assert body["args"] == ARGS
    assert body["completion_time"] is not None


async def test_get_run_for_missing_execution_is_not_found(client_factory: Callable[..., Any]) -> None:
    async with client_factory() as client:
        response = await client.get(f"/runs/{MISSING_EXECUTION_ID}")

    assert response.status_code == 404


async def test_get_run_logs_returns_what_the_execution_wrote(
    client_factory: Callable[..., Any], job_runner: LocalJobRunner
) -> None:
    execution_id = await run_to_completion(job_runner, job_name=JOB_NAME, args=ARGS)

    async with client_factory() as client:
        response = await client.get(f"/runs/{execution_id}/logs")

    assert response.status_code == 200
    lines = response.json()["lines"]
    assert [line["message"] for line in lines] == [JOB_LOG_LINE]
    assert lines[0]["severity"] == "INFO"


async def test_get_run_logs_for_missing_execution_is_not_found(client_factory: Callable[..., Any]) -> None:
    async with client_factory() as client:
        response = await client.get(f"/runs/{MISSING_EXECUTION_ID}/logs")

    assert response.status_code == 404
