import base64
import json
from datetime import UTC, datetime

import pytest
from mocks import FakeSender, FakeSendingClient
from pytest_mock import MockerFixture

from library.infrastructure.errors import InfrastructureError
from library_provider_azure.messaging import ServiceBusEventBus, ServiceBusTaskQueue, queue_name_for
from library_provider_azure.settings import SERVICE_BUS_NAMESPACE, SERVICE_BUS_QUEUES_JSON

NAMESPACE = "acme.servicebus.windows.net"
QUEUE_NAME = "notes-reindex"
QUEUES_JSON = json.dumps({"notes:reindex": QUEUE_NAME})


@pytest.fixture(autouse=True)
def _namespace(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv(SERVICE_BUS_NAMESPACE, NAMESPACE)
    monkeypatch.setenv(SERVICE_BUS_QUEUES_JSON, QUEUES_JSON)


@pytest.fixture
def service_bus(mocker: MockerFixture) -> FakeSendingClient:
    client = FakeSendingClient(sender=FakeSender())
    mocker.patch("library_provider_azure.messaging.AzureClients.service_bus", return_value=client)
    return client


class TestTheEventBus:
    async def test_the_payload_travels_base64_encoded(self, service_bus: FakeSendingClient) -> None:
        await ServiceBusEventBus().publish(topic_name="notes", messages=[{"data": "the payload", "attributes": {}}])

        assert base64.b64decode(str(service_bus.sender.sent[0])).decode() == "the payload"

    async def test_the_attributes_become_the_application_properties_the_subscription_filters_on(
        self, service_bus: FakeSendingClient
    ) -> None:
        await ServiceBusEventBus().publish(
            topic_name="notes", messages=[{"data": "x", "attributes": {"event": "NoteCreated", "service": "notes"}}]
        )

        assert service_bus.sender.sent[0].application_properties == {"event": "NoteCreated", "service": "notes"}

    async def test_every_message_carries_the_id_that_is_returned_for_it(self, service_bus: FakeSendingClient) -> None:
        message_ids = await ServiceBusEventBus().publish(
            topic_name="notes", messages=[{"data": "one"}, {"data": "two"}]
        )

        assert [message.message_id for message in service_bus.sender.sent] == message_ids
        assert len(set(message_ids)) == 2

    async def test_the_messages_reach_the_named_topic(self, service_bus: FakeSendingClient) -> None:
        await ServiceBusEventBus().publish(topic_name="pr7notes", messages=[{"data": "x"}])

        assert service_bus.topics == ["pr7notes"]

    async def test_publishing_nothing_touches_no_topic(self, service_bus: FakeSendingClient) -> None:
        assert await ServiceBusEventBus().publish(topic_name="notes", messages=[]) == []
        assert service_bus.topics == []


class TestTheTaskQueue:
    def test_a_command_is_routed_by_the_queue_the_estate_declared(self) -> None:
        assert queue_name_for(service="notes", task="reindex") == QUEUE_NAME

    def test_an_undeclared_command_has_nowhere_to_go(self) -> None:
        with pytest.raises(InfrastructureError, match="No Service Bus queue is declared"):
            queue_name_for(service="notes", task="absent")

    def test_the_url_names_the_queue_and_the_command(self) -> None:
        url = ServiceBusTaskQueue().get_url(service="notes", task="reindex")

        assert url == f"sb://{NAMESPACE}/{QUEUE_NAME}/commands/reindex"

    def test_params_become_a_query_string_on_the_same_url(self) -> None:
        queue = ServiceBusTaskQueue()

        assert queue.get_url(service="notes", task="reindex", params={"page": "2"}) == (
            f"{queue.get_url(service='notes', task='reindex')}?page=2"
        )

    async def test_the_body_params_and_headers_travel_with_the_message(self, service_bus: FakeSendingClient) -> None:
        await ServiceBusTaskQueue().add_task(
            service="notes",
            task="reindex",
            body={"note_id": "note_1"},
            params={"command_id": "cmd_1"},
            headers={"x-invoking-service": "notes"},
        )

        sent = service_bus.sender.sent[0]
        assert service_bus.queues == [QUEUE_NAME]
        assert json.loads(str(sent)) == {"note_id": "note_1"}
        assert json.loads(sent.application_properties["params"]) == {"command_id": "cmd_1"}
        assert json.loads(sent.application_properties["headers"]) == {"x-invoking-service": "notes"}

    async def test_a_delay_becomes_a_scheduled_enqueue_time(self, service_bus: FakeSendingClient) -> None:
        scheduled_time = datetime(2026, 1, 1, tzinfo=UTC)

        await ServiceBusTaskQueue().add_task(service="notes", task="reindex", body={}, scheduled_time=scheduled_time)

        assert service_bus.sender.sent[0].scheduled_enqueue_time_utc == scheduled_time

    async def test_an_immediate_task_is_not_scheduled(self, service_bus: FakeSendingClient) -> None:
        await ServiceBusTaskQueue().add_task(service="notes", task="reindex", body={})

        assert service_bus.sender.sent[0].scheduled_enqueue_time_utc is None
