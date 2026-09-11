from library.application.unit_of_work import IUnitOfWork
from library.domain.value_objects.users import OrganizationID, UserID
from library.logs import add_log_context
from notes_service.application.notes.dtos import NoteRead
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteTitle
from notes_service.domain.repositories import INoteRepository


class CreateNoteUseCase:
    def __init__(self, *, note_repository: INoteRepository, unit_of_work: IUnitOfWork) -> None:
        self._note_repository = note_repository
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        organization_id: OrganizationID,
        author_id: UserID,
        title: NoteTitle,
        body: NoteBody,
    ) -> NoteRead:
        note = Note.create(organization_id=organization_id, author_id=author_id, title=title, body=body)
        add_log_context(note_id=note.id)

        async with self._unit_of_work():
            await self._note_repository.save(note)

        return NoteRead(
            id=note.id,
            title=note.title,
            status=note.status,
            summary=note.summary,
            created_at=note.created_at,
        )
