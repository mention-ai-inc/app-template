from library.application.unit_of_work import IUnitOfWork
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID
from library.logs import add_log_context
from notes_service.domain.aggregates.note.value_objects import NoteStatus
from notes_service.domain.interfaces.summarizer import ISummarizer
from notes_service.domain.repositories import INoteRepository


class SummarizeNoteUseCase:
    def __init__(
        self,
        *,
        note_repository: INoteRepository,
        summarizer: ISummarizer,
        unit_of_work: IUnitOfWork,
    ) -> None:
        self._note_repository = note_repository
        self._summarizer = summarizer
        self._unit_of_work = unit_of_work

    async def execute(self, *, organization_id: OrganizationID, note_id: NoteID) -> None:
        add_log_context(note_id=note_id)

        async with self._unit_of_work():
            note = await self._note_repository.get(note_id, organization_id=organization_id)

        if note.status == NoteStatus.SUMMARIZED:
            add_log_context(early_return_reason="already_summarized")
            return

        summary = await self._summarizer.summarize(organization_id=organization_id, title=note.title, body=note.body)

        async with self._unit_of_work():
            note = await self._note_repository.get(note_id, organization_id=organization_id)
            note.record_summary(summary=summary)
            await self._note_repository.save(note)

        add_log_context(outcome="summarized")
