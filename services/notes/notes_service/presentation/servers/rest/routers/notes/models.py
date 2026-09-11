from pydantic import BaseModel

from notes_service.application.notes.dtos import NoteRead
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteTitle


class CreateNoteRequest(BaseModel):
    title: NoteTitle
    body: NoteBody


class ListNotesResponse(BaseModel):
    notes: list[NoteRead]
