from notes_service.application.notes.queries import INoteQueryService
from notes_service.infrastructure.queries.notes import NoteQueryService


def get_note_query_service() -> INoteQueryService:
    return NoteQueryService()
