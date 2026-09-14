from typing import Annotated

from fastapi import Depends

from library.domain.commands.notes import SummarizeNote
from library.presentation.api.app import executor
from notes_service.application.notes.use_cases.summarize import SummarizeNoteUseCase
from notes_service.presentation.dependencies.use_cases.notes import get_summarize_note_use_case


@executor
async def endpoint(
    command: SummarizeNote,
    use_case: Annotated[SummarizeNoteUseCase, Depends(get_summarize_note_use_case)],
) -> None:
    await use_case.execute(organization_id=command.organization_id, note_id=command.note_id)
