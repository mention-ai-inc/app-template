from datetime import datetime

from library._testutils.repository import InMemoryRepository
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID
from notes_service.domain.aggregates.note.aggregate import Note, NoteCommand, NoteEvent
from notes_service.domain.repositories import INoteRepository


class InMemoryNoteRepository(InMemoryRepository[Note, NoteID, NoteEvent, NoteCommand], INoteRepository):
    async def list_created_before(self, *, organization_id: OrganizationID, cutoff: datetime, limit: int) -> list[Note]:
        expired = [
            note.model_copy(deep=True)
            for (org, _), note in self._aggregates.items()
            if org == organization_id and note.created_at < cutoff
        ]
        return expired[:limit]
