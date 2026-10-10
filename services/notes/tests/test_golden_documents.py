import json
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic_core import to_jsonable_python

from control_plane.domain.value_objects.common import Service
from control_plane.domain.value_objects.users import OrganizationID, UserID
from control_plane.infrastructure.unit_of_work import unit_of_work
from control_plane.providers.local.database import LocalDatabase
from control_plane.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from control_plane.providers.registry import reset_cloud_provider, set_cloud_provider
from library.domain.value_objects.notes import NoteID
from library.infrastructure.repository import Repository
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteStatus, NoteSummary, NoteTitle

FIXTURES = Path(__file__).resolve().parents[3] / "control-plane/tests/fixtures/documents"

FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
ORGANIZATION_ID = OrganizationID("org_golden")
NOTE_ID = NoteID("note-golden")


@pytest.fixture(autouse=True)
def _local_provider(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.delenv("FEATURE_ENVIRONMENT", raising=False)
    LocalDatabase.clear()
    set_cloud_provider(LOCAL_PROVIDER)
    yield
    reset_cloud_provider()
    LocalDatabase.clear()


def canonical(document: Any, /) -> bytes:
    return (json.dumps(to_jsonable_python(document), indent=2, sort_keys=True) + "\n").encode()


def golden(name: str, /) -> bytes:
    return canonical(json.loads((FIXTURES / f"{name}.json").read_text()))


async def emit_note() -> dict[str, Any]:
    note = Note(
        id=NOTE_ID,
        organization_id=ORGANIZATION_ID,
        author_id=UserID("user_golden"),
        title=NoteTitle("Golden note"),
        body=NoteBody("The body of the golden note."),
        status=NoteStatus.SUMMARIZED,
        summary=NoteSummary("A golden summary."),
        created_at=FIXED_TIME,
    )
    async with unit_of_work():
        await Repository(aggregate=Note, identity_type=NoteID, service=Service.NOTES).save(note)
    document = LocalDatabase.read(collection_id=f"notes_{ORGANIZATION_ID}_note", document_id=NOTE_ID)
    assert document is not None
    return {key: value for key, value in document.data.items() if key != "_subcollection_metadata"}


async def test_a_stored_note_matches_the_golden_document() -> None:
    assert canonical(await emit_note()) == golden("note")
