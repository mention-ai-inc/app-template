from datetime import UTC, datetime
from typing import Any

import pytest

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.jobs import (
    _as_job_execution,  # pyright: ignore[reportPrivateUsage]
    _execution_name_of,  # pyright: ignore[reportPrivateUsage]
)

JOB_NAME = "testadmin-j-backfill"
EXECUTION_ID = f"{JOB_NAME}-x4k9p"
ARGS = ["run", "known-backfill", "--apply"]


def _execution(*, status: str) -> dict[str, Any]:
    return {
        "name": EXECUTION_ID,
        "properties": {
            "status": status,
            "startTime": "2026-07-26T10:00:05Z",
            "endTime": "2026-07-26T10:01:00Z",
            "template": {"containers": [{"name": "app", "args": ARGS}]},
        },
    }


class TestExecutionNames:
    def test_a_started_job_names_its_execution(self) -> None:
        assert _execution_name_of({"name": EXECUTION_ID}, job_name=JOB_NAME) == EXECUTION_ID

    def test_an_execution_name_is_prefixed_with_its_job(self) -> None:
        assert _execution_name_of({"name": EXECUTION_ID}, job_name=JOB_NAME).startswith(f"{JOB_NAME}-")

    def test_a_start_that_named_nothing_is_not_found(self) -> None:
        with pytest.raises(InfrastructureError) as error:
            _execution_name_of({}, job_name=JOB_NAME)

        assert error.value.error_type == InfrastructureErrorType.NOT_FOUND_ERROR


class TestExecutionStatus:
    def test_a_succeeded_execution_reports_success(self) -> None:
        execution = _as_job_execution(_execution(status="Succeeded"), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.status == "succeeded"
        assert execution.succeeded_count == 1

    @pytest.mark.parametrize("status", ["Failed", "Degraded", "Stopped", "Cancelled"])
    def test_every_unhappy_ending_is_a_failure(self, status: str) -> None:
        execution = _as_job_execution(_execution(status=status), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.status == "failed"
        assert execution.failed_count == 1

    @pytest.mark.parametrize("status", ["Running", "Processing"])
    def test_a_live_execution_is_running(self, status: str) -> None:
        execution = _as_job_execution(_execution(status=status), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.status == "running"

    def test_an_unrecognised_status_is_pending_rather_than_terminal(self) -> None:
        execution = _as_job_execution(_execution(status="Unknown"), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.status == "pending"


class TestExecutionDetail:
    def test_the_arguments_come_from_the_container_override(self) -> None:
        execution = _as_job_execution(_execution(status="Succeeded"), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.args == ARGS

    def test_the_timestamps_travel(self) -> None:
        execution = _as_job_execution(_execution(status="Succeeded"), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.started_at == datetime(2026, 7, 26, 10, 0, 5, tzinfo=UTC)
        assert execution.completed_at == datetime(2026, 7, 26, 10, 1, tzinfo=UTC)
