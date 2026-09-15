import base64
import json
import os
import signal
from typing import Any

import pytest
from fastapi import FastAPI, Request
from mocks import FakeLockRenewer, FakeMessage, FakeReceiver, FakeServiceBusClient
from pytest_mock import MockerFixture

from library.infrastructure.errors import InfrastructureError
from library.presentation.api.environment import ComponentType
from library_provider_azure.pools import AzurePoolDriver, ServiceBusSource
from library_provider_azure.settings import (
    CHANGE_FEED_TRIGGERS_JSON,
    SERVICE_BUS_QUEUES_JSON,
    SERVICE_BUS_SUBSCRIPTIONS_JSON,
)

QUEUE_NAME = "notes-summarize-note"
SUBSCRIPTION_NAME = "notes-summarize-note-0"
TOPIC_NAME = "notes"
QUEUES_JSON = json.dumps({"notes:summarize_note": QUEUE_NAME})
SUBSCRIPTIONS_JSON = json.dumps(
    {"notes:summarize_note": [{"topic_name": TOPIC_NAME, "subscription_name": SUBSCRIPTION_NAME}]}
)
TRIGGERS_JSON = json.dumps(
    {
        "notes:submit_command": {
            "trigger_name": "submit_command",
            "container_name": "notes",
            "lease_container_name": "notes-submit-command-leases",
            "document_type": "notes_commands",
        }
    }
)


@pytest.fixture
def received() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def pool(received: list[dict[str, Any]]) -> FastAPI:
    app = FastAPI()

    @app.post("/commands/summarize_note", name="summarize_note")
    async def summarize_note(request: Request) -> None:
        received.append(
            {
                "body": (await request.body()).decode(),
                "query": request.url.query,
                "headers": dict(request.headers),
            }
        )

    @app.post("/events/summarize_note", name="summarize_note_event")
    async def summarize_note_event(request: Request) -> None:
        received.append({"body": (await request.body()).decode()})

    return app


@pytest.fixture
def failing_pool() -> FastAPI:
    app = FastAPI()

    @app.post("/commands/summarize_note", name="summarize_note")
    async def summarize_note() -> None:
        raise RuntimeError("the handler blew up")

    return app


def terminate_this_process() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


class TestRoutingTables:
    def test_an_executor_pool_consumes_the_queue_of_every_command_it_hosts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(SERVICE_BUS_QUEUES_JSON, QUEUES_JSON)

        sources = AzurePoolDriver().service_bus_sources(
            routes={"summarize_note": "/commands/summarize_note"}, component=ComponentType.EXECUTOR
        )

        assert sources == [
            ServiceBusSource(route_name="summarize_note", path="/commands/summarize_note", queue_name=QUEUE_NAME)
        ]

    def test_an_executor_pool_ignores_a_queue_it_does_not_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(SERVICE_BUS_QUEUES_JSON, json.dumps({**json.loads(QUEUES_JSON), "notes:other": "other"}))

        sources = AzurePoolDriver().service_bus_sources(
            routes={"summarize_note": "/commands/summarize_note"}, component=ComponentType.EXECUTOR
        )

        assert [source.queue_name for source in sources] == [QUEUE_NAME]

    def test_a_listener_pool_consumes_every_subscription_of_every_listener_it_hosts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(SERVICE_BUS_SUBSCRIPTIONS_JSON, SUBSCRIPTIONS_JSON)

        sources = AzurePoolDriver().service_bus_sources(
            routes={"summarize_note": "/events/summarize_note"}, component=ComponentType.LISTENER
        )

        assert [(source.topic_name, source.subscription_name) for source in sources] == [
            (TOPIC_NAME, SUBSCRIPTION_NAME)
        ]

    def test_a_listener_pool_also_drains_the_dead_letter_sub_queue_when_the_app_has_a_route_for_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(SERVICE_BUS_SUBSCRIPTIONS_JSON, SUBSCRIPTIONS_JSON)

        sources = AzurePoolDriver().service_bus_sources(
            routes={
                "summarize_note": "/events/summarize_note",
                "summarize_note_dead_letter": "/events/summarize_note/deadletter",
            },
            component=ComponentType.LISTENER,
        )

        assert [source.dead_letter for source in sources] == [False, True]

    def test_a_pool_with_nothing_to_consume_refuses_to_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(SERVICE_BUS_QUEUES_JSON, QUEUES_JSON)

        with pytest.raises(InfrastructureError, match="No executor in this pool has anything to consume"):
            AzurePoolDriver().service_bus_sources(routes={"other": "/commands/other"}, component=ComponentType.EXECUTOR)

    def test_a_trigger_pool_reads_its_container_leases_and_document_type_from_the_routing_table(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(CHANGE_FEED_TRIGGERS_JSON, TRIGGERS_JSON)

        sources = AzurePoolDriver().change_feed_sources(routes={"submit_command": "/triggers/submit_command"})

        assert [(source.container_name, source.lease_container_name, source.document_type) for source in sources] == [
            ("notes", "notes-submit-command-leases", "notes_commands")
        ]


class TestReplayingThePushThatNeverArrived:
    def test_a_command_becomes_the_post_cloud_tasks_would_have_made(self) -> None:
        message = FakeMessage(
            body='{"note_id": "note_1"}',
            application_properties={
                "route": "summarize_note",
                "params": json.dumps({"command_id": "cmd_1"}),
                "headers": json.dumps({"x-invoking-service": "notes"}),
            },
        )

        path, content, headers = AzurePoolDriver().to_request(
            message=message.as_received(),
            source=ServiceBusSource(
                route_name="summarize_note", path="/commands/summarize_note", queue_name=QUEUE_NAME
            ),
            component=ComponentType.EXECUTOR,
        )

        assert path == "/commands/summarize_note?command_id=cmd_1"
        assert content == '{"note_id": "note_1"}'
        assert headers["x-invoking-service"] == "notes"
        assert headers["x-cloudtasks-taskretrycount"] == "0"

    def test_a_redelivery_tells_the_handler_which_attempt_it_is(self) -> None:
        message = FakeMessage(delivery_count=3)

        _, _, headers = AzurePoolDriver().to_request(
            message=message.as_received(),
            source=ServiceBusSource(
                route_name="summarize_note", path="/commands/summarize_note", queue_name=QUEUE_NAME
            ),
            component=ComponentType.EXECUTOR,
        )

        assert headers["x-cloudtasks-taskretrycount"] == "2"

    def test_an_event_becomes_the_post_pubsub_would_have_made(self) -> None:
        message = FakeMessage(
            body=base64.b64encode(b"the payload").decode(),
            application_properties={"event": "NoteCreated", "service": "notes"},
        )

        path, content, _ = AzurePoolDriver().to_request(
            message=message.as_received(),
            source=ServiceBusSource(
                route_name="summarize_note", path="/events/summarize_note", subscription_name=SUBSCRIPTION_NAME
            ),
            component=ComponentType.LISTENER,
        )

        envelope = json.loads(content)
        assert path == "/events/summarize_note"
        assert base64.b64decode(envelope["data"]).decode() == "the payload"
        assert envelope["attributes"] == {"event": "NoteCreated", "service": "notes"}
        assert envelope["message_id"] == "message-1"


class TestDelivery:
    async def test_a_command_reaches_the_handler_and_the_message_is_completed(
        self, pool: FastAPI, received: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        receiver = FakeReceiver(
            messages=[
                FakeMessage(
                    body='{"note_id": "note_1"}',
                    application_properties={
                        "params": json.dumps({"command_id": "cmd_1"}),
                        "headers": json.dumps({"x-invoking-service": "notes"}),
                    },
                )
            ],
            on_empty=terminate_this_process,
        )
        self.__install(mocker, monkeypatch, receiver)

        await AzurePoolDriver()(app=pool, routes={"summarize_note": "/commands/summarize_note"})

        assert [entry["body"] for entry in received] == ['{"note_id": "note_1"}']
        assert received[0]["query"] == "command_id=cmd_1"
        assert len(receiver.completed) == 1
        assert receiver.abandoned == []

    async def test_a_failing_handler_abandons_the_message_for_service_bus_to_redeliver(
        self, failing_pool: FastAPI, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        receiver = FakeReceiver(messages=[FakeMessage()], on_empty=terminate_this_process)
        self.__install(mocker, monkeypatch, receiver)

        await AzurePoolDriver()(app=failing_pool, routes={"summarize_note": "/commands/summarize_note"})

        assert receiver.completed == []
        assert len(receiver.abandoned) == 1

    async def test_every_message_has_its_lock_renewed_while_the_handler_runs(
        self, pool: FastAPI, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        receiver = FakeReceiver(messages=[FakeMessage()], on_empty=terminate_this_process)
        renewers = self.__install(mocker, monkeypatch, receiver)

        await AzurePoolDriver()(app=pool, routes={"summarize_note": "/commands/summarize_note"})

        assert [len(renewer.registered) for renewer in renewers] == [1]

    async def test_a_termination_signal_stops_the_pool(
        self, pool: FastAPI, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        receiver = FakeReceiver(messages=[], on_empty=terminate_this_process)
        self.__install(mocker, monkeypatch, receiver)

        await AzurePoolDriver()(app=pool, routes={"summarize_note": "/commands/summarize_note"})

        assert receiver.drained is True

    def __install(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, receiver: FakeReceiver
    ) -> list[FakeLockRenewer]:
        monkeypatch.setenv("COMPONENT_TYPE", ComponentType.EXECUTOR.value)
        monkeypatch.setenv(SERVICE_BUS_QUEUES_JSON, QUEUES_JSON)
        mocker.patch(
            "library_provider_azure.pools.AzureClients.service_bus",
            return_value=FakeServiceBusClient(receivers={QUEUE_NAME: receiver}),
        )

        renewers: list[FakeLockRenewer] = []

        def make_renewer(*args: object, **kwargs: object) -> FakeLockRenewer:
            renewer = FakeLockRenewer(*args, **kwargs)
            renewers.append(renewer)
            return renewer

        mocker.patch("library_provider_azure.pools.AutoLockRenewer", side_effect=make_renewer)
        return renewers


async def test_a_pool_refuses_to_start_when_its_component_type_is_not_declared(
    pool: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("COMPONENT_TYPE", raising=False)

    with pytest.raises(InfrastructureError, match="COMPONENT_TYPE"):
        await AzurePoolDriver()(app=pool, routes={})
