from library._testutils.unit_of_work import FakeUnitOfWork
from library.domain.events.notes import NoteSummarized
from library.domain.value_objects.users import OrganizationID, UserID
from notes_service.application.notes.use_cases.summarize import SummarizeNoteUseCase
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteStatus, NoteSummary, NoteTitle
from tests.stubs.repositories import InMemoryNoteRepository
from tests.stubs.services import FakeSummarizer


async def test_summarize_records_the_summarizer_output() -> None:
    note_repository = InMemoryNoteRepository()
    note = __make_note()
    note.request_summary()
    await note_repository.seed(note, organization_id=__org())
    summarizer = FakeSummarizer(response=NoteSummary("Ship on Tuesday."))
    use_case = __build_use_case(note_repository=note_repository, summarizer=summarizer)

    await use_case.execute(organization_id=__org(), note_id=note.id)

    saved = await note_repository.quick_get(note.id, organization_id=__org())
    assert saved.status == NoteStatus.SUMMARIZED
    assert saved.summary == NoteSummary("Ship on Tuesday.")
    assert summarizer.last_call is not None
    assert (summarizer.last_call.title, summarizer.last_call.body) == (note.title, note.body)
    assert [event.payload for event in note_repository.published_events] == [
        NoteSummarized(organization_id=__org(), note_id=note.id)
    ]


async def test_summarize_returns_early_when_already_summarized() -> None:
    note_repository = InMemoryNoteRepository()
    note = __make_note()
    note.record_summary(summary=NoteSummary("Already done."))
    await note_repository.seed(note, organization_id=__org())
    summarizer = FakeSummarizer()
    use_case = __build_use_case(note_repository=note_repository, summarizer=summarizer)

    await use_case.execute(organization_id=__org(), note_id=note.id)

    assert summarizer.call_count == 0
    assert note_repository.published_events == []


def __build_use_case(
    *,
    note_repository: InMemoryNoteRepository,
    summarizer: FakeSummarizer | None = None,
) -> SummarizeNoteUseCase:
    return SummarizeNoteUseCase(
        note_repository=note_repository,
        summarizer=summarizer or FakeSummarizer(),
        unit_of_work=FakeUnitOfWork(),
    )


def __org() -> OrganizationID:
    return OrganizationID("org_1")


def __make_note() -> Note:
    return Note.create(
        organization_id=__org(),
        author_id=UserID("user_1"),
        title=NoteTitle("Release plan"),
        body=NoteBody("Ship on Tuesday after the QA pass."),
    )
