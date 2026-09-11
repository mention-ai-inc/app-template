from library.application.unit_of_work import IUnitOfWork
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID
from library.logs import add_log_context
from notes_service.domain.aggregates.note.value_objects import NoteStatus
from notes_service.domain.repositories import INoteRepository


class RequestNoteSummaryUseCase:
    def __init__(self, *, note_repository: INoteRepository, unit_of_work: IUnitOfWork) -> None:
        self._note_repository = note_repository
        self._unit_of_work = unit_of_work

    async def execute(self, *, organization_id: OrganizationID, note_id: NoteID) -> None:
        add_log_context(note_id=note_id)

        async with self._unit_of_work():
            note = await self._note_repository.get(note_id, organization_id=organization_id)
            if note.status != NoteStatus.PENDING:
                add_log_context(early_return_reason="summary_already_requested")
                return

            note.request_summary()
            await self._note_repository.save(note)
