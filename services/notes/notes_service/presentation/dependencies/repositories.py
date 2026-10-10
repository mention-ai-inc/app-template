from notes_service.domain.repositories import INoteRepository
from notes_service.infrastructure.persistence.notes import NoteRepository


def get_note_repository() -> INoteRepository:
    return NoteRepository()
