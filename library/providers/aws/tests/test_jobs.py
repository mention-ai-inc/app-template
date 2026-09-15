from datetime import UTC, datetime
from typing import Any

import pytest

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_aws.jobs import _as_job_execution, task_id_from, task_id_of  # pyright: ignore[reportPrivateUsage]
from library_provider_aws.logs import log_group_for, log_stream_for

JOB_NAME = "testadmin-j-backfill"
TASK_ID = "9f8e7d6c5b4a3210"
EXECUTION_ID = f"{JOB_NAME}-{TASK_ID}"
ARGS = ["run", "known-backfill", "--apply"]


def _task(*, last_status: str, exit_codes: list[int | None] | None = None) -> dict[str, Any]:
    containers: list[dict[str, Any]] = [{"name": "app"}]
    if exit_codes is not None:
        containers = [{"name": "app", "exitCode": code} for code in exit_codes]
    return {
        "taskArn": f"arn:aws:ecs:us-east-1:123456789012:task/cluster/{TASK_ID}",
        "lastStatus": last_status,
        "containers": containers,
        "overrides": {"containerOverrides": [{"name": "app", "command": ARGS}]},
        "createdAt": datetime(2026, 7, 26, 10, 0, tzinfo=UTC),
        "startedAt": datetime(2026, 7, 26, 10, 0, 5, tzinfo=UTC),
        "stoppedAt": datetime(2026, 7, 26, 10, 1, tzinfo=UTC),
    }


class TestExecutionIdentifiers:
    def test_a_task_id_is_the_last_segment_of_its_arn(self) -> None:
        assert task_id_of(f"arn:aws:ecs:us-east-1:123456789012:task/cluster/{TASK_ID}") == TASK_ID

    def test_an_execution_id_gives_back_the_task_it_names(self) -> None:
        assert task_id_from(EXECUTION_ID, job_name=JOB_NAME) == TASK_ID

    def test_an_execution_id_from_another_job_is_not_found(self) -> None:
        with pytest.raises(InfrastructureError) as error:
            task_id_from("testadmin-j-seed-abc", job_name=JOB_NAME)

        assert error.value.error_type == InfrastructureErrorType.NOT_FOUND_ERROR


class TestExecutionStatus:
    @pytest.mark.parametrize("last_status", ["PROVISIONING", "PENDING"])
    def test_a_task_that_has_not_started_is_pending(self, last_status: str) -> None:
        execution = _as_job_execution(_task(last_status=last_status), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.status == "pending"

    @pytest.mark.parametrize("last_status", ["ACTIVATING", "RUNNING", "DEACTIVATING", "STOPPING", "DEPROVISIONING"])
    def test_a_task_on_its_way_anywhere_else_is_running(self, last_status: str) -> None:
        execution = _as_job_execution(_task(last_status=last_status), execution_id=EXECUTION_ID, job_name=JOB_NAME)

        assert execution.status == "running"

    def test_a_task_that_stopped_cleanly_succeeded(self) -> None:
        execution = _as_job_execution(
            _task(last_status="STOPPED", exit_codes=[0]), execution_id=EXECUTION_ID, job_name=JOB_NAME
        )

        assert execution.status == "succeeded"
        assert execution.succeeded_count == 1

    def test_a_non_zero_exit_code_failed(self) -> None:
        execution = _as_job_execution(
            _task(last_status="STOPPED", exit_codes=[1]), execution_id=EXECUTION_ID, job_name=JOB_NAME
        )

        assert execution.status == "failed"
        assert execution.failed_count == 1

    def test_a_container_that_never_reported_an_exit_code_failed(self) -> None:
        execution = _as_job_execution(
            _task(last_status="STOPPED", exit_codes=[None]), execution_id=EXECUTION_ID, job_name=JOB_NAME
        )

        assert execution.status == "failed"


class TestExecutionDetail:
    def test_the_arguments_come_from_the_container_override(self) -> None:
        execution = _as_job_execution(
            _task(last_status="STOPPED", exit_codes=[0]), execution_id=EXECUTION_ID, job_name=JOB_NAME
        )

        assert execution.args == ARGS

    def test_the_timestamps_travel(self) -> None:
        execution = _as_job_execution(
            _task(last_status="STOPPED", exit_codes=[0]), execution_id=EXECUTION_ID, job_name=JOB_NAME
        )

        assert execution.created_at == datetime(2026, 7, 26, 10, 0, tzinfo=UTC)
        assert execution.started_at == datetime(2026, 7, 26, 10, 0, 5, tzinfo=UTC)
        assert execution.completed_at == datetime(2026, 7, 26, 10, 1, tzinfo=UTC)


class TestLogAddressing:
    def test_a_job_writes_to_its_own_log_group(self) -> None:
        assert log_group_for(JOB_NAME) == f"/ecs/{JOB_NAME}"

    def test_a_task_writes_to_the_stream_the_awslogs_driver_names(self) -> None:
        assert log_stream_for(TASK_ID) == f"app/app/{TASK_ID}"
