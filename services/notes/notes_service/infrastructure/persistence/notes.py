from datetime import datetime

from library.application.ports.documents import QueryFilter
from library.domain.value_objects.common import Service
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.repository import Repository
from notes_service.domain.aggregates.note.aggregate import Note, NoteCommand, NoteEvent
from notes_service.domain.repositories import INoteRepository


class NoteRepository(Repository[Note, NoteID, NoteEvent, NoteCommand], INoteRepository):
    def __init__(self) -> None:
        super().__init__(aggregate=Note, identity_type=NoteID, service=Service.NOTES)

    async def list_created_before(self, *, organization_id: OrganizationID, cutoff: datetime, limit: int) -> list[Note]:
        with self._aggregate_store.connect_to_partition(organization_id) as store:
            notes = await store.query(
                filters=[QueryFilter(field="created_at", operator="<", value=cutoff)], limit=limit
            )

        return notes.entities
