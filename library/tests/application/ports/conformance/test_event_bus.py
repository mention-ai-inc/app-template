import base64
from collections.abc import Callable

from library.application.ports.eventbus import IEventBus, OutboundMessage
from tests.application.ports.conformance.providers import RecordedMessage

TOPIC_NAME = "conformance-topic"


def _messages() -> list[OutboundMessage]:
    return [
        {"data": "first payload", "attributes": {"event": "notes.created", "service": "notes"}},
        {"data": "second payload", "attributes": {"event": "notes.updated", "service": "notes"}},
    ]


class TestPublishing:
    async def test_publish_returns_one_id_per_message(self, event_bus: IEventBus) -> None:
        message_ids = await event_bus.publish(topic_name=TOPIC_NAME, messages=_messages())

        assert len(message_ids) == 2

    async def test_publish_returns_distinct_ids(self, event_bus: IEventBus) -> None:
        message_ids = await event_bus.publish(topic_name=TOPIC_NAME, messages=_messages())

        assert len(set(message_ids)) == len(message_ids)

    async def test_publishing_nothing_returns_nothing(self, event_bus: IEventBus) -> None:
        assert await event_bus.publish(topic_name=TOPIC_NAME, messages=[]) == []


class TestWhatReachesTheTopic:
    async def test_the_messages_reach_the_named_topic(
        self, event_bus: IEventBus, read_recorded_messages: Callable[[], list[RecordedMessage]]
    ) -> None:
        await event_bus.publish(topic_name=TOPIC_NAME, messages=_messages())

        assert [recorded.topic_name for recorded in read_recorded_messages()] == [TOPIC_NAME, TOPIC_NAME]

    async def test_attributes_survive_the_publish(
        self, event_bus: IEventBus, read_recorded_messages: Callable[[], list[RecordedMessage]]
    ) -> None:
        await event_bus.publish(topic_name=TOPIC_NAME, messages=_messages())

        assert [recorded.attributes["event"] for recorded in read_recorded_messages()] == [
            "notes.created",
            "notes.updated",
        ]

    async def test_the_payload_travels_base64_encoded(
        self, event_bus: IEventBus, read_recorded_messages: Callable[[], list[RecordedMessage]]
    ) -> None:
        await event_bus.publish(topic_name=TOPIC_NAME, messages=_messages())

        assert [base64.b64decode(recorded.data).decode() for recorded in read_recorded_messages()] == [
            "first payload",
            "second payload",
        ]

    async def test_the_returned_ids_identify_the_recorded_messages(
        self, event_bus: IEventBus, read_recorded_messages: Callable[[], list[RecordedMessage]]
    ) -> None:
        message_ids = await event_bus.publish(topic_name=TOPIC_NAME, messages=_messages())

        assert [recorded.message_id for recorded in read_recorded_messages()] == message_ids
