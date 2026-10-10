import asyncio
import json
import stat
from collections.abc import Generator
from pathlib import Path

import pytest

from admin.client.local_jobs import BACKFILL_COMMAND_VARIABLE, register_local_jobs
from control_plane.providers.local.jobs import LocalExecution
from control_plane.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from control_plane.providers.registry import reset_cloud_provider, set_cloud_provider

FAKE_BACKFILL = """#!/bin/bash
echo "FEATURE_ENVIRONMENT=${FEATURE_ENVIRONMENT}"
if [ "$1" = "list" ]; then
    echo '{"backfills": [{"name": "fake", "description": "A fake backfill."}]}'
    exit 0
fi
echo "args: $*"
[ "$2" = "fake" ] || { echo "Unknown backfill '$2'." >&2; exit 1; }
"""


@pytest.fixture(autouse=True)
def _on_the_local_provider(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "dev")
    set_cloud_provider(LOCAL_PROVIDER)
    LOCAL_PROVIDER.job_runner().clear()
    yield
    LOCAL_PROVIDER.job_runner().clear()
    reset_cloud_provider()


@pytest.fixture
def fake_backfill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "backfill"
    script.write_text(FAKE_BACKFILL)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv(BACKFILL_COMMAND_VARIABLE, str(script))


async def run_backfill_job(args: list[str]) -> LocalExecution:
    register_local_jobs()
    runner = LOCAL_PROVIDER.job_runner()
    execution_id = await runner.run_job(job_name="devadmin-j-backfill", args=args)
    while runner.executions[execution_id].status not in ("succeeded", "failed"):
        await asyncio.sleep(0)
    return runner.executions[execution_id]


def messages(execution: LocalExecution) -> list[str]:
    return [line.message for line in execution.lines]


@pytest.mark.usefixtures("fake_backfill")
async def test_list_streams_the_catalogue_line_into_the_execution_logs() -> None:
    execution = await run_backfill_job(["list", "--json"])

    assert execution.status == "succeeded"
    assert "FEATURE_ENVIRONMENT=dev" in messages(execution)
    assert json.dumps({"backfills": [{"name": "fake", "description": "A fake backfill."}]}) in messages(execution)


@pytest.mark.usefixtures("fake_backfill")
async def test_run_passes_the_arguments_through() -> None:
    execution = await run_backfill_job(["run", "fake", "--apply", "--organization-id", "org_1"])

    assert execution.status == "succeeded"
    assert "args: run fake --apply --organization-id org_1" in messages(execution)


@pytest.mark.usefixtures("fake_backfill")
async def test_a_non_zero_exit_fails_the_execution() -> None:
    execution = await run_backfill_job(["run", "unknown"])

    assert execution.status == "failed"
    assert "Unknown backfill 'unknown'." in messages(execution)


async def test_a_missing_command_lists_an_empty_catalogue_with_a_clear_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(BACKFILL_COMMAND_VARIABLE, str(tmp_path / "missing-backfill"))

    execution = await run_backfill_job(["list", "--json"])

    assert execution.status == "succeeded"
    assert any("No backfill command" in message for message in messages(execution))
    assert messages(execution)[-1] == json.dumps({"backfills": []})


async def test_a_missing_command_fails_a_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(BACKFILL_COMMAND_VARIABLE, str(tmp_path / "missing-backfill"))

    execution = await run_backfill_job(["run", "fake"])

    assert execution.status == "failed"
    assert any("No backfill command" in message for message in messages(execution))
