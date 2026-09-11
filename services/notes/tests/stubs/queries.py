from library.domain.value_objects.users import OrganizationID
from notes_service.application.notes.dtos import NoteRead
from notes_service.application.notes.queries import INoteQueryService


class InMemoryNoteQueryService(INoteQueryService):
    def __init__(self, *, notes: dict[OrganizationID, list[NoteRead]] | None = None) -> None:
        self._notes = notes or {}

    async def list_notes(self, *, organization_id: OrganizationID) -> list[NoteRead]:
        return [note.model_copy(deep=True) for note in self._notes.get(organization_id, [])]
