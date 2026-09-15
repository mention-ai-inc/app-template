from collections.abc import Generator

import pytest
from fastapi import FastAPI
from pytest_mock import MockerFixture

from library.presentation.api.runner import run
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from library.providers.registry import reset_cloud_provider, set_cloud_provider


@pytest.fixture(autouse=True)
def _local_provider() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    set_cloud_provider(LOCAL_PROVIDER)
    yield
    reset_cloud_provider()


@pytest.fixture
def pool() -> FastAPI:
    app = FastAPI()

    @app.post("/commands/summarize_note", name="summarize_note")
    async def summarize_note() -> None: ...

    return app


def test_a_push_provider_serves_the_pool_over_http(pool: FastAPI, mocker: MockerFixture) -> None:
    gunicorn = mocker.patch("library.presentation.api.runner.__FastAPIGunicornApplication")

    run(app=pool)

    assert gunicorn.called


def test_a_pull_provider_runs_its_driver_instead_of_serving(pool: FastAPI, mocker: MockerFixture) -> None:
    delivered: list[dict[str, str]] = []

    async def driver(*, app: FastAPI, routes: dict[str, str]) -> None:  # noqa: ARG001
        delivered.append(routes)

    gunicorn = mocker.patch("library.presentation.api.runner.__FastAPIGunicornApplication")
    mocker.patch.object(LOCAL_PROVIDER, "pool_driver", return_value=driver)

    run(app=pool)

    assert delivered == [{"summarize_note": "/commands/summarize_note"}]
    assert not gunicorn.called
