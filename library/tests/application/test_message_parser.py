import base64
from datetime import UTC, datetime

import pytest

from library._testutils.cache import FakeAsyncCache
from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.events import MessageParser
from library.application.ports.cache import IAsyncCache
from library.application.ports.eventbus import InboundEvent
from library.domain.events.base import EventPayload
from library.domain.events.notes import NoteCreated, NoteSummarized
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID


class _AliasPayload(EventPayload):
    value: str

    @classmethod
    def event_name(cls) -> str:
        return "AliasEvent"


def _cache() -> IAsyncCache:
    return FakeAsyncCache()


async def _parse[DataT: EventPayload](
    parser: MessageParser[DataT], *, event: str, payload_json: str
) -> InboundEvent[DataT]:
    return await parser.parse(
        encoded_data=base64.b64encode(payload_json.encode()).decode(),
        raw_attributes={"event": event, "service": "notes"},
        message_id="msg-1",
        publish_time=datetime.now(UTC),
    )


async def test_parses_the_model_named_by_the_event_attribute() -> None:
    parser = MessageParser(data_models=[NoteCreated, NoteSummarized], cache=_cache())
    summarized = NoteSummarized(organization_id=OrganizationID("org_test"), note_id=NoteID())

    event = await _parse(parser, event="NoteSummarized", payload_json=summarized.model_dump_json())

    assert isinstance(event.data, NoteSummarized)
    assert event.data == summarized


async def test_rejects_unhandled_event_name() -> None:
    parser = MessageParser(data_models=[NoteCreated, NoteSummarized], cache=_cache())
    created = NoteCreated(organization_id=OrganizationID("org_test"), note_id=NoteID())

    with pytest.raises(ApplicationError) as exc_info:
        await _parse(parser, event="NotePurged", payload_json=created.model_dump_json())

    assert exc_info.value.error_type == ApplicationErrorType.VALIDATION_ERROR


async def test_uses_event_name_when_it_differs_from_class_name() -> None:
    parser = MessageParser(data_models=[_AliasPayload], cache=_cache())

    event = await _parse(parser, event="AliasEvent", payload_json='{"value": "ok"}')

    assert event.data == _AliasPayload(value="ok")


async def test_a_duplicate_event_id_is_refused_when_deduplication_is_on() -> None:
    parser = MessageParser(data_models=[NoteCreated], cache=_cache(), deduplication_ttl_ms=30_000)
    created = NoteCreated(organization_id=OrganizationID("org_test"), note_id=NoteID())

    async def parse_once() -> InboundEvent[NoteCreated]:
        return await parser.parse(
            encoded_data=base64.b64encode(created.model_dump_json().encode()).decode(),
            raw_attributes={"event": "NoteCreated", "service": "notes", "event_id": "evt_1"},
            message_id="msg-1",
            publish_time=datetime.now(UTC),
        )

    await parse_once()

    with pytest.raises(ApplicationError) as exc_info:
        await parse_once()

    assert exc_info.value.error_type == ApplicationErrorType.PROCESS_FAILED
