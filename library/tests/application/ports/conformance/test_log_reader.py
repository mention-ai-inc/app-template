import pytest

from library.application.ports.jobs import IJobRunner
from library.application.ports.logs import ILogReader
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from tests.application.ports.conformance.providers import CONFORMANCE_LOG_LINE
from tests.application.ports.conformance.test_job_runner import ARGS, MISSING_EXECUTION, wait_for_completion


async def test_an_execution_serves_back_the_lines_it_wrote(
    job_runner: IJobRunner, log_reader: ILogReader, conformance_job: str
) -> None:
    execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)
    await wait_for_completion(job_runner, job_name=conformance_job, execution_id=execution_id)

    lines = await log_reader.read_execution_logs(job_name=conformance_job, execution_id=execution_id)

    assert any(CONFORMANCE_LOG_LINE in line.message for line in lines)


async def test_lines_come_back_oldest_first(
    job_runner: IJobRunner, log_reader: ILogReader, conformance_job: str
) -> None:
    execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)
    await wait_for_completion(job_runner, job_name=conformance_job, execution_id=execution_id)

    lines = await log_reader.read_execution_logs(job_name=conformance_job, execution_id=execution_id)

    assert [line.timestamp for line in lines] == sorted(line.timestamp for line in lines)


async def test_a_limit_caps_the_lines_returned(
    job_runner: IJobRunner, log_reader: ILogReader, conformance_job: str
) -> None:
    execution_id = await job_runner.run_job(job_name=conformance_job, args=ARGS)
    await wait_for_completion(job_runner, job_name=conformance_job, execution_id=execution_id)

    lines = await log_reader.read_execution_logs(job_name=conformance_job, execution_id=execution_id, limit=1)

    assert len(lines) <= 1


async def test_reading_logs_for_a_missing_execution_raises(log_reader: ILogReader, conformance_job: str) -> None:
    with pytest.raises(InfrastructureError) as exc_info:
        await log_reader.read_execution_logs(job_name=conformance_job, execution_id=MISSING_EXECUTION)

    assert exc_info.value.error_type == InfrastructureErrorType.NOT_FOUND_ERROR
