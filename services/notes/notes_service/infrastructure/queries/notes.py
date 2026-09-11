from library.domain.value_objects.users import OrganizationID
from library.infrastructure.persistence.firestore import Firestore, SortBy
from library.infrastructure.service import QueryService
from notes_service.application.notes.dtos import NoteRead
from notes_service.application.notes.queries import INoteQueryService
from notes_service.domain.aggregates.note.aggregate import Note


class NoteQueryService(INoteQueryService, QueryService):
    def __init__(self) -> None:
        self._store = Firestore(collection=Note.get_table_name(), model=Note, partition_key_type=OrganizationID)

    async def list_notes(self, *, organization_id: OrganizationID) -> list[NoteRead]:
        with self._store.connect_to_partition(organization_id) as store:
            notes = await store.query(sort_by=SortBy(field="created_at", direction="DESCENDING"))

        return [
            NoteRead(
                id=note.id,
                title=note.title,
                status=note.status,
                summary=note.summary,
                created_at=note.created_at,
            )
            for note in notes.entities
        ]
