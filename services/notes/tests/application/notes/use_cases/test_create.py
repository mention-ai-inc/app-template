from library._testutils.unit_of_work import FakeUnitOfWork
from library.domain.events.notes import NoteCreated
from library.domain.value_objects.users import OrganizationID, UserID
from notes_service.application.notes.use_cases.create import CreateNoteUseCase
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteStatus, NoteTitle
from tests.stubs.repositories import InMemoryNoteRepository


async def test_create_saves_the_note_and_publishes_note_created() -> None:
    note_repository = InMemoryNoteRepository()
    use_case = __build_use_case(note_repository=note_repository)

    read = await use_case.execute(
        organization_id=__org(),
        author_id=UserID("user_1"),
        title=NoteTitle("Release plan"),
        body=NoteBody("Ship on Tuesday."),
    )

    saved = await note_repository.quick_get(read.id, organization_id=__org())
    assert (saved.title, saved.body, saved.author_id) == ("Release plan", "Ship on Tuesday.", "user_1")
    assert (read.title, read.status, read.summary, read.created_at) == (
        saved.title,
        NoteStatus.PENDING,
        None,
        saved.created_at,
    )
    assert [event.payload for event in note_repository.published_events] == [
        NoteCreated(organization_id=__org(), note_id=read.id)
    ]


def __build_use_case(*, note_repository: InMemoryNoteRepository) -> CreateNoteUseCase:
    return CreateNoteUseCase(note_repository=note_repository, unit_of_work=FakeUnitOfWork())


def __org() -> OrganizationID:
    return OrganizationID("org_1")
