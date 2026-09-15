import json
import os

import httpx
import pytest
from fastapi import FastAPI, Response
from pytest_mock import MockerFixture

from library.presentation.api import error_handling
from library.presentation.api.app import (
    Entrypoint,
    executor,
    executor_pool,
    listener,
    listener_pool,
    trigger,
    trigger_pool,
)
from library.providers.local.messaging import LocalEventBus


async def test_executor_pool_routes_each_command_to_its_own_handler() -> None:
    app = executor_pool({"first_command": __executor(b"first"), "second_command": __executor(b"second")})

    first = await __post(app=app, path="/commands/first_command", headers={"x-invoking-service": "notes"})
    second = await __post(app=app, path="/commands/second_command", headers={"x-invoking-service": "notes"})

    assert first.content == b"first"
    assert second.content == b"second"


async def test_executor_pool_does_not_answer_for_a_command_it_does_not_host() -> None:
    app = executor_pool({"first_command": __executor(b"first")})

    response = await __post(app=app, path="/commands/absent_command", headers={"x-invoking-service": "notes"})

    assert response.status_code == 404


async def test_listener_pool_routes_each_listener_to_its_own_handler() -> None:
    app = listener_pool({"on_note_created": __listener(b"created"), "on_note_deleted": __listener(b"deleted")})

    created = await __post(app=app, path="/events/on_note_created")
    deleted = await __post(app=app, path="/events/on_note_deleted")

    assert created.content == b"created"
    assert deleted.content == b"deleted"


async def test_listener_pool_acknowledges_dead_lettered_messages_per_listener() -> None:
    app = listener_pool({"on_note_created": __listener(b"created")})

    response = await __post(app=app, path="/events/on_note_created/deadletter")

    assert response.status_code == 200


async def test_trigger_pool_routes_each_trigger_to_its_own_handler() -> None:
    app = trigger_pool({"publish_event": __trigger(b"published"), "submit_command": __trigger(b"submitted")})

    published = await __post(app=app, path="/triggers/publish_event")
    submitted = await __post(app=app, path="/triggers/submit_command")

    assert published.content == b"published"
    assert submitted.content == b"submitted"


async def test_a_pool_serves_one_health_endpoint_for_all_of_its_entrypoints() -> None:
    app = executor_pool({"first_command": __executor(b"first"), "second_command": __executor(b"second")})

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        pool_health = await client.get("/health")
        entrypoint_health = await client.get("/commands/first_command/health")

    assert pool_health.status_code == 200
    assert entrypoint_health.status_code == 404


async def test_a_pooled_request_is_logged_against_the_entrypoint_that_served_it(mocker: MockerFixture) -> None:
    info = mocker.patch.object(error_handling.logger, "info")
    app = executor_pool({"first_command": __executor(b"first"), "second_command": __executor(b"second")})

    await __post(app=app, path="/commands/second_command", headers={"x-invoking-service": "notes"})

    assert json.loads(info.call_args.args[0])["component_name"] == "second_command"


async def test_a_pool_refuses_an_entrypoint_of_another_kind() -> None:
    with pytest.raises(ValueError, match="cannot host"):
        executor_pool({"on_note_created": __listener(b"created")})


async def test_a_pool_refuses_to_start_with_nothing_to_serve() -> None:
    with pytest.raises(ValueError, match="at least one entrypoint"):
        listener_pool({})


@pytest.fixture(autouse=True)
def _component_environment(mocker: MockerFixture) -> None:  # pyright: ignore[reportUnusedFunction]
    mocker.patch.dict(os.environ, {"SERVICE": "notes", "COMPONENT_TYPE": "executor"})
    os.environ.pop("COMPONENT_NAME", None)


@pytest.fixture(autouse=True)
def _command_results_go_to_the_in_memory_bus() -> None:  # pyright: ignore[reportUnusedFunction]
    LocalEventBus.clear()


def __executor(body: bytes, /) -> Entrypoint:
    async def endpoint() -> Response:
        return Response(content=body)

    return executor(endpoint)


def __listener(body: bytes, /) -> Entrypoint:
    async def handler() -> Response:
        return Response(content=body)

    return listener(handler)


def __trigger(body: bytes, /) -> Entrypoint:
    async def handler() -> Response:
        return Response(content=body)

    return trigger(handler)


async def __post(*, app: FastAPI, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(path, headers=headers or {})
