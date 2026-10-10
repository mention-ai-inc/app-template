from datetime import datetime

from pydantic import BaseModel

from library.domain.value_objects.notes import NoteID
from notes_service.domain.aggregates.note.value_objects import NoteStatus, NoteSummary, NoteTitle


class NoteRead(BaseModel):
    id: NoteID
    title: NoteTitle
    status: NoteStatus
    summary: NoteSummary | None
    created_at: datetime
