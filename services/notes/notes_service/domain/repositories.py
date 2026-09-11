from datetime import datetime

from library.domain.repositories import IRepository
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID
from notes_service.domain.aggregates.note.aggregate import Note, NoteCommand, NoteEvent


class INoteRepository(IRepository[Note, NoteID, NoteEvent, NoteCommand]):
    async def list_created_before(
        self, *, organization_id: OrganizationID, cutoff: datetime, limit: int
    ) -> list[Note]: ...
