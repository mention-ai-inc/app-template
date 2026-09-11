import pytest
from tests.server.conftest import FakeCloudRun

from admin.server.jobs import JobLauncher, group_for_execution, job_name
from library.application.errors import ApplicationError, ApplicationErrorType


@pytest.fixture(autouse=True)
def feature_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "test")


def test_job_names_are_pinned_per_group() -> None:
    assert job_name("backfill") == "testadmin-j-backfill"
    assert job_name("seed") == "testadmin-j-seed"


async def test_launch_targets_the_group_job_with_args_only(cloud_run: FakeCloudRun) -> None:
    launcher = JobLauncher(cloud_run=cloud_run)

    execution_id = await launcher.launch(group="backfill", args=["run", "some-backfill", "--apply"])

    assert execution_id == "testadmin-j-backfill-abc12"
    assert cloud_run.launches == [{"job_name": "testadmin-j-backfill", "args": ["run", "some-backfill", "--apply"]}]


def test_group_is_recovered_from_execution_id() -> None:
    assert group_for_execution("testadmin-j-backfill-abc12") == "backfill"
    assert group_for_execution("testadmin-j-seed-xyz99") == "seed"


def test_unknown_execution_id_is_not_found() -> None:
    with pytest.raises(ApplicationError) as error:
        group_for_execution("testnotes-j-other-abc12")

    assert error.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND


async def test_missing_execution_is_not_found(cloud_run: FakeCloudRun) -> None:
    launcher = JobLauncher(cloud_run=cloud_run)

    with pytest.raises(ApplicationError) as error:
        await launcher.execution(execution_id="testadmin-j-backfill-missing")

    assert error.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND
