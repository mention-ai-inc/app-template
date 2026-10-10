import os
from unittest.mock import MagicMock

import httpx
import pytest
import sentry_sdk
from fastapi import APIRouter, FastAPI
from pydantic_ai.exceptions import ConcurrencyLimitExceeded, ModelHTTPError
from pytest_mock import MockerFixture

from control_plane.presentation.api.error_handling import ExceptionHandlingRoute
from library.infrastructure.llm.run import translate_model_errors


@pytest.fixture(autouse=True)
def _component_environment(mocker: MockerFixture) -> None:  # pyright: ignore[reportUnusedFunction]
    mocker.patch.dict(os.environ, {"SERVICE": "notes", "COMPONENT_TYPE": "server", "COMPONENT_NAME": "server-notes"})


def test_model_errors_keep_the_upstream_status_code() -> None:
    translation = translate_model_errors(ModelHTTPError(status_code=429, model_name="gemini-3.6-flash"))

    assert translation is not None
    assert translation[0] == 429


def test_concurrency_limits_report_the_service_as_overloaded() -> None:
    translation = translate_model_errors(ConcurrencyLimitExceeded("too many"))

    assert translation is not None
    assert translation[0] == 503


def test_other_errors_are_left_to_the_control_plane() -> None:
    assert translate_model_errors(RuntimeError("boom")) is None


async def test_upstream_provider_throttling_is_captured_by_sentry(mocker: MockerFixture) -> None:
    capture = __patch_capture(mocker)

    response = await __request(error=ModelHTTPError(status_code=429, model_name="anthropic:claude-sonnet-4-5"))

    assert response.status_code == 429
    assert capture.call_count == 1


def __patch_capture(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(sentry_sdk, "capture_exception")


async def __request(*, error: Exception) -> httpx.Response:
    async def endpoint() -> None:
        raise error

    router = APIRouter(route_class=ExceptionHandlingRoute)
    router.add_api_route("/boom", endpoint, methods=["GET"])
    app = FastAPI()
    app.include_router(router)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/boom")
