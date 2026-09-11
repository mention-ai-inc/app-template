from typing import Annotated

from fastapi import APIRouter, Depends

from library.presentation.auth.types import AuthenticatedUser
from library.presentation.auth.user import get_user
from notes_service.application.notes.dtos import NoteRead
from notes_service.application.notes.use_cases.create import CreateNoteUseCase
from notes_service.application.notes.use_cases.list import ListNotesUseCase
from notes_service.presentation.dependencies.use_cases.notes import get_create_note_use_case, get_list_notes_use_case
from notes_service.presentation.servers.rest.routers.notes.models import CreateNoteRequest, ListNotesResponse

notes_router = APIRouter(prefix="/notes", tags=["Notes"])


@notes_router.get("")
async def list_notes(
    user: Annotated[AuthenticatedUser, Depends(get_user)],
    use_case: Annotated[ListNotesUseCase, Depends(get_list_notes_use_case)],
) -> ListNotesResponse:
    notes = await use_case.execute(organization_id=user.organization_id)
    return ListNotesResponse(notes=notes)


@notes_router.post("")
async def create_note(
    body: CreateNoteRequest,
    user: Annotated[AuthenticatedUser, Depends(get_user)],
    use_case: Annotated[CreateNoteUseCase, Depends(get_create_note_use_case)],
) -> NoteRead:
    return await use_case.execute(
        organization_id=user.organization_id,
        author_id=user.uid,
        title=body.title,
        body=body.body,
    )
