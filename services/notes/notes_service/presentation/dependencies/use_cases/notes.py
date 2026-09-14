from typing import Annotated

from fastapi import Depends

from library.application.ports.unit_of_work import IUnitOfWork
from library.application.ports.users import IUsersClient
from library.presentation.dependencies import get_unit_of_work, get_users_client
from notes_service.application.notes.queries import INoteQueryService
from notes_service.application.notes.use_cases.create import CreateNoteUseCase
from notes_service.application.notes.use_cases.list import ListNotesUseCase
from notes_service.application.notes.use_cases.purge import PurgeNotesUseCase
from notes_service.application.notes.use_cases.request_summary import RequestNoteSummaryUseCase
from notes_service.application.notes.use_cases.summarize import SummarizeNoteUseCase
from notes_service.domain.interfaces.summarizer import ISummarizer
from notes_service.domain.repositories import INoteRepository
from notes_service.presentation.dependencies.infrastructure_services import get_summarizer
from notes_service.presentation.dependencies.queries import get_note_query_service
from notes_service.presentation.dependencies.repositories import get_note_repository


def get_create_note_use_case(
    note_repository: Annotated[INoteRepository, Depends(get_note_repository)],
    unit_of_work: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> CreateNoteUseCase:
    return CreateNoteUseCase(note_repository=note_repository, unit_of_work=unit_of_work)


def get_list_notes_use_case(
    note_query_service: Annotated[INoteQueryService, Depends(get_note_query_service)],
) -> ListNotesUseCase:
    return ListNotesUseCase(note_query_service=note_query_service)


def get_request_note_summary_use_case(
    note_repository: Annotated[INoteRepository, Depends(get_note_repository)],
    unit_of_work: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> RequestNoteSummaryUseCase:
    return RequestNoteSummaryUseCase(note_repository=note_repository, unit_of_work=unit_of_work)


def get_summarize_note_use_case(
    note_repository: Annotated[INoteRepository, Depends(get_note_repository)],
    summarizer: Annotated[ISummarizer, Depends(get_summarizer)],
    unit_of_work: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> SummarizeNoteUseCase:
    return SummarizeNoteUseCase(note_repository=note_repository, summarizer=summarizer, unit_of_work=unit_of_work)


def get_purge_notes_use_case(
    note_repository: Annotated[INoteRepository, Depends(get_note_repository)],
    users_client: Annotated[IUsersClient, Depends(get_users_client)],
    unit_of_work: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> PurgeNotesUseCase:
    return PurgeNotesUseCase(note_repository=note_repository, users_client=users_client, unit_of_work=unit_of_work)
