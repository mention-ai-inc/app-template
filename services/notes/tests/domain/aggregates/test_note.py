from datetime import UTC, datetime, timedelta

import pytest

from library.domain.commands.notes import SummarizeNote
from library.domain.errors import DomainError
from library.domain.events.notes import NoteCreated, NoteSummarized
from library.domain.value_objects.users import OrganizationID, UserID
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteStatus, NoteSummary, NoteTitle


def test_create_starts_pending_and_emits_note_created() -> None:
    note = __make_note()

    assert note.status == NoteStatus.PENDING
    assert note.summary is None
    assert [event.payload for event in note.events] == [NoteCreated(organization_id=__org(), note_id=note.id)]


def test_create_rejects_a_blank_title() -> None:
    with pytest.raises(DomainError):
        __make_note(title="   ")


def test_create_rejects_a_blank_body() -> None:
    with pytest.raises(DomainError):
        __make_note(body="")


def test_request_summary_dispatches_summarize_note_once() -> None:
    note = __make_note()
    note.mark_published()

    note.request_summary()
    note.request_summary()

    assert note.status == NoteStatus.SUMMARIZING
    assert [command.payload for command in note.commands] == [SummarizeNote(organization_id=__org(), note_id=note.id)]


def test_record_summary_stores_the_summary_and_emits_note_summarized() -> None:
    note = __make_note()
    note.request_summary()
    note.mark_published()

    note.record_summary(summary=NoteSummary("Ship on Tuesday."))

    assert note.status == NoteStatus.SUMMARIZED
    assert note.summary == NoteSummary("Ship on Tuesday.")
    assert [event.payload for event in note.events] == [NoteSummarized(organization_id=__org(), note_id=note.id)]


def test_request_summary_after_summarized_does_nothing() -> None:
    note = __make_note()
    note.request_summary()
    note.record_summary(summary=NoteSummary("Done."))
    note.mark_published()

    note.request_summary()

    assert note.status == NoteStatus.SUMMARIZED
    assert note.commands == []


def test_purge_cutoff_is_retention_before_the_given_moment() -> None:
    as_of = datetime(2026, 9, 11, tzinfo=UTC)

    assert Note.purge_cutoff(as_of=as_of) == as_of - timedelta(days=90)


def __org() -> OrganizationID:
    return OrganizationID("org_1")


def __make_note(*, title: str = "Release plan", body: str = "Ship on Tuesday after the QA pass.") -> Note:
    return Note.create(
        organization_id=__org(),
        author_id=UserID("user_1"),
        title=NoteTitle(title),
        body=NoteBody(body),
    )
