from library._testutils.unit_of_work import FakeUnitOfWork
from library.domain.commands.notes import SummarizeNote
from library.domain.value_objects.users import OrganizationID, UserID
from notes_service.application.notes.use_cases.request_summary import RequestNoteSummaryUseCase
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteStatus, NoteTitle
from tests.stubs.repositories import InMemoryNoteRepository


async def test_request_summary_dispatches_summarize_note() -> None:
    note_repository = InMemoryNoteRepository()
    note = __make_note()
    await note_repository.seed(note, organization_id=__org())
    use_case = __build_use_case(note_repository=note_repository)

    await use_case.execute(organization_id=__org(), note_id=note.id)

    saved = await note_repository.quick_get(note.id, organization_id=__org())
    assert saved.status == NoteStatus.SUMMARIZING
    assert [command.payload for command in note_repository.published_commands] == [
        SummarizeNote(organization_id=__org(), note_id=note.id)
    ]


async def test_request_summary_returns_early_when_already_requested() -> None:
    note_repository = InMemoryNoteRepository()
    note = __make_note()
    note.request_summary()
    await note_repository.seed(note, organization_id=__org())
    use_case = __build_use_case(note_repository=note_repository)

    await use_case.execute(organization_id=__org(), note_id=note.id)

    assert note_repository.published_commands == []


def __build_use_case(*, note_repository: InMemoryNoteRepository) -> RequestNoteSummaryUseCase:
    return RequestNoteSummaryUseCase(note_repository=note_repository, unit_of_work=FakeUnitOfWork())


def __org() -> OrganizationID:
    return OrganizationID("org_1")


def __make_note() -> Note:
    return Note.create(
        organization_id=__org(),
        author_id=UserID("user_1"),
        title=NoteTitle("Release plan"),
        body=NoteBody("Ship on Tuesday."),
    )
