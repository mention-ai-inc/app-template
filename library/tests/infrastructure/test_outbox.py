import os
from collections.abc import Generator
from typing import Any

import pytest

from library.domain.commands.base import CommandPayload
from library.domain.events.base import EventPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.outbox import CommandDispatcher, EventPublisher
from library.infrastructure.unit_of_work import unit_of_work
from library.providers.local.database import LocalDatabase
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from library.providers.registry import reset_cloud_provider, set_cloud_provider

ORGANIZATION_ID = OrganizationID("org_outbox")
OTHER_ORGANIZATION_ID = OrganizationID("org_other")


class SummarizeNote(CommandPayload):
    SERVICE = Service.NOTES

    note_id: str


class NoteSummarized(EventPayload):
    note_id: str


@pytest.fixture(autouse=True)
def _local_provider(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv("SERVICE", Service.NOTES)
    monkeypatch.delenv("FEATURE_ENVIRONMENT", raising=False)
    LocalDatabase.clear()
    set_cloud_provider(LOCAL_PROVIDER)
    yield
    reset_cloud_provider()
    LocalDatabase.clear()


def _stored(collection: str) -> dict[str, dict[str, Any]]:
    stored = LocalDatabase.read_all(collection_id=f"{os.getenv('FEATURE_ENVIRONMENT', '')}notes_{collection}")
    return {document_id: document.data for document_id, document in stored.items()}


async def test_commands_stay_in_one_flat_collection_the_change_feed_can_watch() -> None:
    dispatcher = CommandDispatcher()

    async with unit_of_work():
        await dispatcher.save(SummarizeNote(note_id="note-1"), organization_id=ORGANIZATION_ID)
        await dispatcher.save(SummarizeNote(note_id="note-2"), organization_id=OTHER_ORGANIZATION_ID)

    assert len(_stored("commands")) == 2
    assert LocalDatabase.read_all(collection_id=f"notes_{ORGANIZATION_ID}_commands") == {}


async def test_a_dispatched_command_carries_its_organization_as_the_partition_value() -> None:
    dispatcher = CommandDispatcher()

    async with unit_of_work():
        command_id = await dispatcher.save(SummarizeNote(note_id="note-1"), organization_id=ORGANIZATION_ID)

    stored = _stored("commands")
    assert command_id in stored
    assert stored[command_id]["organization_id"] == ORGANIZATION_ID


async def test_a_published_event_carries_its_organization_as_the_partition_value() -> None:
    publisher = EventPublisher()

    async with unit_of_work():
        event_id = await publisher.save(NoteSummarized(note_id="note-1"), organization_id=ORGANIZATION_ID)

    stored = _stored("events")
    assert event_id in stored
    assert stored[event_id]["organization_id"] == ORGANIZATION_ID


async def test_a_command_and_an_event_for_one_organization_share_a_partition_value() -> None:
    dispatcher = CommandDispatcher()
    publisher = EventPublisher()

    async with unit_of_work():
        await dispatcher.save(SummarizeNote(note_id="note-1"), organization_id=ORGANIZATION_ID)
        await publisher.save(NoteSummarized(note_id="note-1"), organization_id=ORGANIZATION_ID)

    partitions = {
        *(document["organization_id"] for document in _stored("commands").values()),
        *(document["organization_id"] for document in _stored("events").values()),
    }
    assert partitions == {ORGANIZATION_ID}


async def test_two_organizations_do_not_share_a_partition_value() -> None:
    dispatcher = CommandDispatcher()

    async with unit_of_work():
        await dispatcher.save(SummarizeNote(note_id="note-1"), organization_id=ORGANIZATION_ID)
        await dispatcher.save(SummarizeNote(note_id="note-2"), organization_id=OTHER_ORGANIZATION_ID)

    partitions = {document["organization_id"] for document in _stored("commands").values()}
    assert partitions == {ORGANIZATION_ID, OTHER_ORGANIZATION_ID}


async def test_an_aborted_unit_of_work_dispatches_nothing() -> None:
    dispatcher = CommandDispatcher()

    with pytest.raises(RuntimeError):
        async with unit_of_work():
            await dispatcher.save(SummarizeNote(note_id="note-1"), organization_id=ORGANIZATION_ID)
            raise RuntimeError

    assert _stored("commands") == {}


async def test_quick_save_writes_without_a_unit_of_work() -> None:
    dispatcher = CommandDispatcher()

    command_id = await dispatcher.quick_save(SummarizeNote(note_id="note-1"), organization_id=ORGANIZATION_ID)

    assert command_id in _stored("commands")
