import pytest

from library.domain.commands.base import Command
from library.domain.commands.notes import SummarizeNote
from library.domain.events.base import Event
from library.domain.events.notes import NoteCreated, NoteSummarized
from library.domain.value_objects.common import Service
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID


def test_note_events_round_trip_through_json() -> None:
    note_id = NoteID()
    for payload_type in (NoteCreated, NoteSummarized):
        payload = payload_type(organization_id=OrganizationID("org_test"), note_id=note_id)

        parsed = payload_type.model_validate_json(payload.model_dump_json())

        assert parsed == payload
        assert parsed.note_id == note_id
        assert payload_type.event_name() == payload_type.__name__


def test_event_name_is_the_payload_class_name() -> None:
    event = Event(
        organization_id=OrganizationID("org_test"),
        payload=NoteCreated(organization_id=OrganizationID("org_test"), note_id=NoteID()),
    )

    assert event.name == "NoteCreated"


def test_summarize_note_command_targets_the_notes_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE", "notes")
    command = Command(
        organization_id=OrganizationID("org_test"),
        payload=SummarizeNote(organization_id=OrganizationID("org_test"), note_id=NoteID()),
    )

    assert SummarizeNote.SERVICE == Service.NOTES
    assert command.executor_name == "summarize_note"
