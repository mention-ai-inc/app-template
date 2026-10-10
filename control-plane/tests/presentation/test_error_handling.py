import os
from unittest.mock import MagicMock

import httpx
import pytest
import sentry_sdk
from fastapi import APIRouter, FastAPI
from pytest_mock import MockerFixture

from control_plane.domain.errors import DomainError, DomainErrorType
from control_plane.presentation.api.error_handling import (
    ExceptionHandlingRoute,
    ExceptionTranslation,
    register_exception_translator,
)
from control_plane.presentation.errors import PresentationError, PresentationErrorType


@pytest.fixture(autouse=True)
def _component_environment(mocker: MockerFixture) -> None:  # pyright: ignore[reportUnusedFunction]
    mocker.patch.dict(os.environ, {"SERVICE": "notes", "COMPONENT_TYPE": "server", "COMPONENT_NAME": "server-notes"})


async def test_domain_quota_error_is_not_captured_by_sentry(mocker: MockerFixture) -> None:
    capture = __patch_capture(mocker)

    response = await __request(error=DomainError(error_type=DomainErrorType.QUOTA_ERROR, message="Quota exhausted."))

    assert response.status_code == 429
    assert capture.call_count == 0


async def test_presentation_quota_error_is_not_captured_by_sentry(mocker: MockerFixture) -> None:
    capture = __patch_capture(mocker)

    response = await __request(
        error=PresentationError(
            error_type=PresentationErrorType.QUOTA_ERROR,
            message="Organization org_1 has exhausted its quota.",
        )
    )

    assert response.status_code == 429
    assert capture.call_count == 0


class UpstreamThrottled(Exception):
    pass


def __translate_upstream_throttling(exception: Exception, /) -> ExceptionTranslation | None:
    if isinstance(exception, UpstreamThrottled):
        return 429, "Upstream throttled.", str(exception)
    return None


async def test_a_registered_translator_decides_the_status_and_is_captured_by_sentry(mocker: MockerFixture) -> None:
    capture = __patch_capture(mocker)
    register_exception_translator(__translate_upstream_throttling)

    response = await __request(error=UpstreamThrottled("slow down"))

    assert response.status_code == 429
    assert response.json() == {"detail": "Upstream throttled."}
    assert capture.call_count == 1


async def test_unexpected_error_is_captured_by_sentry(mocker: MockerFixture) -> None:
    capture = __patch_capture(mocker)

    response = await __request(error=RuntimeError("boom"))

    assert response.status_code == 500
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
