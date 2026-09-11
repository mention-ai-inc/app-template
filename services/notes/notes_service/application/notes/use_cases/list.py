from library.domain.value_objects.users import OrganizationID
from notes_service.application.notes.dtos import NoteRead
from notes_service.application.notes.queries import INoteQueryService


class ListNotesUseCase:
    def __init__(self, *, note_query_service: INoteQueryService) -> None:
        self._note_query_service = note_query_service

    async def execute(self, *, organization_id: OrganizationID) -> list[NoteRead]:
        return await self._note_query_service.list_notes(organization_id=organization_id)
