from typing import Protocol

from library.domain.value_objects.users import OrganizationID
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteSummary, NoteTitle


class ISummarizer(Protocol):
    async def summarize(self, *, organization_id: OrganizationID, title: NoteTitle, body: NoteBody) -> NoteSummary: ...
