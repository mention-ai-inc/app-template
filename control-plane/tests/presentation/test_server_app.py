import os
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from pytest_mock import MockerFixture

from control_plane.presentation.api.app import create_server_app


class WidgetRequest(BaseModel):
    name: str


class WidgetResponse(BaseModel):
    name: str


def test_operation_ids_are_the_route_names() -> None:
    schema = __schema()

    assert schema["paths"]["/rest/widgets/widgets"]["get"]["operationId"] == "list_widgets"
    assert schema["paths"]["/rest/widgets/widgets"]["post"]["operationId"] == "create_widget"
    assert schema["paths"]["/rest/widgets/health"]["get"]["operationId"] == "health"


def test_operations_carry_their_explicit_summaries_and_tags() -> None:
    schema = __schema()

    assert schema["paths"]["/rest/widgets/widgets"]["get"]["summary"] == "List widgets"
    assert schema["paths"]["/rest/widgets/widgets"]["get"]["tags"] == ["Widgets"]
    assert schema["paths"]["/rest/widgets/health"]["get"]["summary"] == "Health"
    assert schema["paths"]["/rest/widgets/health"]["get"]["tags"] == ["Health"]


def test_a_post_answers_200_and_no_validation_error_response() -> None:
    schema = __schema()

    assert list(schema["paths"]["/rest/widgets/widgets"]["post"]["responses"]) == ["200"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert "ValidationError" not in schema["components"]["schemas"]


def test_bearer_authentication_is_the_security_scheme() -> None:
    schema = __schema()

    assert schema["components"]["securitySchemes"] == {"HTTPBearer": {"type": "http", "scheme": "bearer"}}
    assert schema["paths"]["/rest/widgets/widgets"]["get"]["security"] == [{"HTTPBearer": []}]


def test_the_served_schema_is_the_pinned_one() -> None:
    app = __app()

    assert app.openapi() is app.openapi()
    assert "422" not in app.openapi()["paths"]["/rest/widgets/widgets"]["post"]["responses"]


@pytest.fixture(autouse=True)
def _component_environment(mocker: MockerFixture) -> None:  # pyright: ignore[reportUnusedFunction]
    mocker.patch.dict(os.environ, {"SERVICE": "widgets", "COMPONENT_TYPE": "server"})


def __schema() -> dict[str, Any]:
    return __app().openapi()


def __app() -> FastAPI:
    router = APIRouter(prefix="/widgets", tags=["Widgets"])

    @router.get("", summary="List widgets")
    async def list_widgets(
        token: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],  # noqa: ARG001
    ) -> list[WidgetResponse]:
        return []

    @router.post("", summary="Create a widget")
    async def create_widget(
        body: WidgetRequest,
        token: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],  # noqa: ARG001
    ) -> WidgetResponse:
        return WidgetResponse(name=body.name)

    return create_server_app(description="Widgets", routers=[router])
