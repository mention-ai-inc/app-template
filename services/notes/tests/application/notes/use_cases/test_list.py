from datetime import UTC, datetime

from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID
from notes_service.application.notes.dtos import NoteRead
from notes_service.application.notes.use_cases.list import ListNotesUseCase
from notes_service.domain.aggregates.note.value_objects import NoteStatus, NoteTitle
from tests.stubs.queries import InMemoryNoteQueryService


async def test_list_returns_only_the_organizations_notes() -> None:
    mine = __note_read("Release plan")
    query_service = InMemoryNoteQueryService(
        notes={__org(): [mine], OrganizationID("org_other"): [__note_read("Not mine")]}
    )
    use_case = ListNotesUseCase(note_query_service=query_service)

    notes = await use_case.execute(organization_id=__org())

    assert notes == [mine]


def __org() -> OrganizationID:
    return OrganizationID("org_1")


def __note_read(title: str) -> NoteRead:
    return NoteRead(
        id=NoteID(),
        title=NoteTitle(title),
        status=NoteStatus.PENDING,
        summary=None,
        created_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
