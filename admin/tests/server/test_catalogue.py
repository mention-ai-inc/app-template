import json
import logging

import pytest
from tests.server.conftest import JOB_IMAGE, KNOWN_BACKFILL, launches

from admin.server.catalogue import LIST_ARGS, BackfillCatalogue, BackfillEntry, parse_catalogue
from admin.server.jobs import JobLauncher
from control_plane.application.errors import ApplicationError, ApplicationErrorType
from control_plane.logs import SIMPLE_LOGGER_NAME
from control_plane.providers.local.jobs import LocalJobRunner, LocalLogReader

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


@pytest.fixture(autouse=True)
def feature_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "test")


def catalogue_for(job_runner: LocalJobRunner) -> BackfillCatalogue:
    return BackfillCatalogue(
        launcher=JobLauncher(job_runner=job_runner),
        log_reader=LocalLogReader(runner=job_runner),
        poll_interval_seconds=0,
    )


async def test_the_catalogue_is_read_from_the_list_execution_logs(catalogue: BackfillCatalogue) -> None:
    assert await catalogue.list() == [BackfillEntry(name="known-backfill", description="A test backfill.")]


async def test_the_catalogue_is_cached_between_calls(catalogue: BackfillCatalogue, job_runner: LocalJobRunner) -> None:
    await catalogue.list()
    await catalogue.list()
    assert await catalogue.has("known-backfill")
    assert not await catalogue.has("other-backfill")

    assert launches(job_runner) == [{"job_name": "testadmin-j-backfill", "args": LIST_ARGS}]


async def test_the_cache_is_per_environment(
    monkeypatch: pytest.MonkeyPatch, catalogue: BackfillCatalogue, job_runner: LocalJobRunner
) -> None:
    await catalogue.list()
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "")
    await catalogue.list()

    assert [launch["job_name"] for launch in launches(job_runner)] == ["testadmin-j-backfill", "admin-j-backfill"]


async def test_other_log_lines_around_the_catalogue_are_ignored() -> None:
    async def chatty_list(args: list[str]) -> None:  # noqa: ARG001
        logger.info("Starting up")
        logger.info(json.dumps({"backfills": [KNOWN_BACKFILL]}))
        logger.info("Done")

    runner = LocalJobRunner()
    runner.register(job_name="testadmin-j-backfill", handler=chatty_list, image=JOB_IMAGE)

    assert await catalogue_for(runner).list() == [BackfillEntry(name="known-backfill", description="A test backfill.")]


async def test_an_execution_without_a_catalogue_line_fails() -> None:
    async def silent_list(args: list[str]) -> None:  # noqa: ARG001
        logger.info("Nothing to report")

    runner = LocalJobRunner()
    runner.register(job_name="testadmin-j-backfill", handler=silent_list)

    with pytest.raises(ApplicationError) as error:
        await catalogue_for(runner).list()

    assert error.value.error_type == ApplicationErrorType.PROCESS_FAILED
    assert "reported no backfill catalogue" in error.value.message


async def test_a_failed_execution_is_not_cached() -> None:
    attempts: list[int] = []

    async def flaky_list(args: list[str]) -> None:  # noqa: ARG001
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("boom")
        logger.info(json.dumps({"backfills": []}))

    runner = LocalJobRunner()
    runner.register(job_name="testadmin-j-backfill", handler=flaky_list)
    catalogue = catalogue_for(runner)

    with pytest.raises(ApplicationError):
        await catalogue.list()

    assert await catalogue.list() == []
    assert len(attempts) == 2


def test_parse_catalogue_returns_none_without_a_catalogue_line() -> None:
    assert parse_catalogue(["Working...", "{'not': 'json'}"]) is None


def test_parse_catalogue_rejects_a_malformed_line() -> None:
    with pytest.raises(ApplicationError) as error:
        parse_catalogue(['{"backfills": [{"name": "missing-description"}]}'])

    assert error.value.error_type == ApplicationErrorType.PROCESS_FAILED
