import asyncio

import pytest

from library.application.ports.jobs import IJobRunner, JobExecution
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType

ARGS = ["run", "conformance", "--apply"]
MISSING_EXECUTION = "conformance-job-missing"
TERMINAL_STATUSES = ("succeeded", "failed")
POLL_TIMEOUT_SECONDS = 30.0
POLL_INTERVAL_SECONDS = 0.05


async def wait_for_completion(job_runner: IJobRunner, *, job_name: str, execution_id: str) -> JobExecution:
    deadline = asyncio.get_running_loop().time() + POLL_TIMEOUT_SECONDS
    while True:
        execution = await job_runner.get_execution(job_name=job_name, execution_id=execution_id)
        if execution.status in TERMINAL_STATUSES:
            return execution
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"{execution_id} was still {execution.status} after {POLL_TIMEOUT_SECONDS}s")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


class TestRunningAJob:
    async def test_an_execution_id_is_prefixed_with_the_job_name(
        self, job_runner: IJobRunner, conformance_job: str
    ) -> None:
        execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)

        assert execution_id.startswith(f"{conformance_job}-")

    async def test_two_runs_are_two_executions(self, job_runner: IJobRunner, conformance_job: str) -> None:
        first = await job_runner.run_job(job_name=conformance_job, args=ARGS)
        second = await job_runner.run_job(job_name=conformance_job, args=ARGS)

        assert first != second

    async def test_the_execution_carries_the_arguments_it_was_given(
        self, job_runner: IJobRunner, conformance_job: str
    ) -> None:
        execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)

        execution = await wait_for_completion(job_runner, job_name=conformance_job, execution_id=execution_id)

        assert execution.args == ARGS

    async def test_a_job_that_completes_reports_success(self, job_runner: IJobRunner, conformance_job: str) -> None:
        execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)

        execution = await wait_for_completion(job_runner, job_name=conformance_job, execution_id=execution_id)

        assert execution.status == "succeeded"
        assert execution.succeeded_count == 1
        assert execution.completed_at is not None


class TestReadingAnExecution:
    async def test_an_execution_reports_the_job_it_belongs_to(
        self, job_runner: IJobRunner, conformance_job: str
    ) -> None:
        execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)

        execution = await job_runner.get_execution(job_name=conformance_job, execution_id=execution_id)

        assert execution.job_name == conformance_job
        assert execution.execution_id == execution_id

    async def test_reading_a_missing_execution_raises(self, job_runner: IJobRunner, conformance_job: str) -> None:
        with pytest.raises(InfrastructureError) as exc_info:
            await job_runner.get_execution(job_name=conformance_job, execution_id=MISSING_EXECUTION)

        assert exc_info.value.error_type == InfrastructureErrorType.NOT_FOUND_ERROR


class TestReadingAJob:
    async def test_a_job_reports_its_own_name(self, job_runner: IJobRunner, conformance_job: str) -> None:
        job = await job_runner.get_job(job_name=conformance_job)

        assert job.job_name == conformance_job

    async def test_reading_a_missing_job_raises(self, job_runner: IJobRunner, conformance_job: str) -> None:  # noqa: ARG002
        with pytest.raises(InfrastructureError) as exc_info:
            await job_runner.get_job(job_name="no-such-job")

        assert exc_info.value.error_type == InfrastructureErrorType.NOT_FOUND_ERROR
