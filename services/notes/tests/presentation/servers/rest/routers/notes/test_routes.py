from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from library._testutils.unit_of_work import FakeUnitOfWork
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID, UserID
from library.infrastructure.users import ClerkRole
from library.presentation.api.app import create_server_app
from library.presentation.auth.types import AuthenticatedUser
from library.presentation.auth.user import get_user
from notes_service.application.notes.dtos import NoteRead
from notes_service.application.notes.use_cases.create import CreateNoteUseCase
from notes_service.application.notes.use_cases.list import ListNotesUseCase
from notes_service.domain.aggregates.note.value_objects import NoteStatus, NoteSummary, NoteTitle
from notes_service.presentation.dependencies.use_cases.notes import get_create_note_use_case, get_list_notes_use_case
from notes_service.presentation.servers.rest.routers.notes.routes import notes_router
from tests.stubs.queries import InMemoryNoteQueryService
from tests.stubs.repositories import InMemoryNoteRepository


@pytest.fixture(autouse=True)
def _component_environment(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv("COMPONENT_TYPE", "server")
    monkeypatch.setenv("COMPONENT_NAME", "rest")


async def test_list_notes_returns_the_organizations_notes() -> None:
    note = NoteRead(
        id=NoteID(),
        title=NoteTitle("Release plan"),
        status=NoteStatus.SUMMARIZED,
        summary=NoteSummary("Ship on Tuesday."),
        created_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    app = __build_app(query_service=InMemoryNoteQueryService(notes={__org(): [note]}))

    async with __client(app) as client:
        response = await client.get("/rest/notes/notes")

    assert response.status_code == 200
    assert response.json() == {
        "notes": [
            {
                "id": note.id,
                "title": "Release plan",
                "status": "summarized",
                "summary": "Ship on Tuesday.",
                "created_at": "2026-09-11T00:00:00Z",
            }
        ]
    }


async def test_create_note_saves_it_for_the_authenticated_user() -> None:
    note_repository = InMemoryNoteRepository()
    app = __build_app(note_repository=note_repository)

    async with __client(app) as client:
        response = await client.post("/rest/notes/notes", json={"title": "Release plan", "body": "Ship on Tuesday."})

    assert response.status_code == 200
    created = response.json()
    assert (created["title"], created["status"], created["summary"]) == ("Release plan", "pending", None)
    saved = await note_repository.quick_get(NoteID(created["id"]), organization_id=__org())
    assert (saved.author_id, saved.body) == ("user_1", "Ship on Tuesday.")


async def test_create_note_rejects_a_blank_title() -> None:
    app = __build_app()

    async with __client(app) as client:
        response = await client.post("/rest/notes/notes", json={"title": "  ", "body": "Ship on Tuesday."})

    assert response.status_code == 400


def __org() -> OrganizationID:
    return OrganizationID("org_1")


def __user() -> AuthenticatedUser:
    return AuthenticatedUser.model_validate(
        {
            "token": "token",
            "uid": UserID("user_1"),
            "organization_id": __org(),
            "clerk_role": ClerkRole.MEMBER,
            "organization_public_metadata": {},
        }
    )


def __build_app(
    *,
    note_repository: InMemoryNoteRepository | None = None,
    query_service: InMemoryNoteQueryService | None = None,
) -> FastAPI:
    app = create_server_app(description="Notes", routers=[notes_router], prefix="/rest/notes")
    app.dependency_overrides[get_user] = __user
    app.dependency_overrides[get_create_note_use_case] = lambda: CreateNoteUseCase(
        note_repository=note_repository or InMemoryNoteRepository(), unit_of_work=FakeUnitOfWork()
    )
    app.dependency_overrides[get_list_notes_use_case] = lambda: ListNotesUseCase(
        note_query_service=query_service or InMemoryNoteQueryService()
    )
    return app


def __client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
