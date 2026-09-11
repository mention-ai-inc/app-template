from typing import Annotated

from fastapi import Depends

from library.application.events import PubSubEvent
from library.domain.events.notes import NoteCreated
from library.presentation.api.app import listener
from library.presentation.api.runner import run
from library.presentation.dependencies import get_message_parser
from notes_service.application.notes.use_cases.request_summary import RequestNoteSummaryUseCase
from notes_service.presentation.dependencies.use_cases.notes import get_request_note_summary_use_case


@listener
async def handler(
    message: Annotated[PubSubEvent[NoteCreated], Depends(get_message_parser(data_models=[NoteCreated]))],
    use_case: Annotated[RequestNoteSummaryUseCase, Depends(get_request_note_summary_use_case)],
) -> None:
    await use_case.execute(organization_id=message.data.organization_id, note_id=message.data.note_id)


def main() -> None:
    run(app=handler)
