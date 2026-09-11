from typing import Protocol

from library.domain.value_objects.users import OrganizationID
from notes_service.application.notes.dtos import NoteRead


class INoteQueryService(Protocol):
    async def list_notes(self, *, organization_id: OrganizationID) -> list[NoteRead]: ...
