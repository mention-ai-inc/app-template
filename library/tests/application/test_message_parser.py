import base64
from datetime import UTC, datetime

import pytest

from library._testutils.cache import FakeAsyncCache
from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.events import MessageParser, PubSubMessage, PubSubMessageMessage
from library.application.ports.cache import IAsyncCache
from library.domain.events.base import EventPayload
from library.domain.events.notes import NoteCreated, NoteSummarized
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID


class _AliasPayload(EventPayload):
    value: str

    @classmethod
    def event_name(cls) -> str:
        return "AliasEvent"


def _pubsub_message(*, event: str, payload_json: str) -> PubSubMessage:
    return PubSubMessage(
        message=PubSubMessageMessage(
            data=base64.b64encode(payload_json.encode()).decode(),
            attributes={"event": event, "service": "notes"},
            message_id="msg-1",
            publish_time=datetime.now(UTC),
        )
    )


def _cache() -> IAsyncCache:
    return FakeAsyncCache()


async def test_parses_the_model_named_by_the_event_attribute() -> None:
    parser = MessageParser(data_models=[NoteCreated, NoteSummarized], cache=_cache())
    summarized = NoteSummarized(organization_id=OrganizationID("org_test"), note_id=NoteID())

    event = await parser(_pubsub_message(event="NoteSummarized", payload_json=summarized.model_dump_json()))

    assert isinstance(event.data, NoteSummarized)
    assert event.data == summarized


async def test_rejects_unhandled_event_name() -> None:
    parser = MessageParser(data_models=[NoteCreated, NoteSummarized], cache=_cache())
    created = NoteCreated(organization_id=OrganizationID("org_test"), note_id=NoteID())

    with pytest.raises(ApplicationError) as error:
        await parser(_pubsub_message(event="NotePurged", payload_json=created.model_dump_json()))

    assert error.value.error_type == ApplicationErrorType.VALIDATION_ERROR


async def test_uses_event_name_when_it_differs_from_class_name() -> None:
    parser = MessageParser(data_models=[_AliasPayload], cache=_cache())

    event = await parser(_pubsub_message(event="AliasEvent", payload_json='{"value": "ok"}'))

    assert isinstance(event.data, _AliasPayload)
    assert event.data.value == "ok"
