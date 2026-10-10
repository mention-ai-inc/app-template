import json
import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic_core import to_jsonable_python
from pytest_mock import MockerFixture

from control_plane._testutils.cache import FakeAsyncCache
from control_plane.application.audit.context import (
    flush_audit_context,
    init_audit_context,
    set_actor,
    set_causation_id,
    set_correlation_id,
    set_request_metadata,
    set_source,
)
from control_plane.application.ports.eventbus import OutboundMessage
from control_plane.domain.audit.action import AuditAction
from control_plane.domain.audit.actor import AuditActor, AuditActorType
from control_plane.domain.audit.change import FieldChange
from control_plane.domain.audit.event import AuditEventID, AuditSource
from control_plane.domain.events.base import EventID, EventRead
from control_plane.domain.value_objects.common import Service
from control_plane.domain.value_objects.users import OrganizationID
from control_plane.infrastructure.audit.publisher import AuditEventPublisher
from control_plane.infrastructure.unit_of_work import unit_of_work
from control_plane.providers.local.database import LocalDatabase
from control_plane.providers.local.messaging import LocalTaskQueue
from control_plane.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from control_plane.providers.registry import reset_cloud_provider, set_cloud_provider
from library.domain.commands.base import CommandID, CommandRead
from library.domain.commands.notes import SummarizeNote
from library.domain.events.notes import NoteCreated
from library.domain.value_objects.notes import NoteID
from library.infrastructure.outbox import CommandDispatcher, EventPublisher
from library.presentation.service.triggers.publish_event import publish_event
from library.presentation.service.triggers.submit_command import submit_command

FIXTURES = Path(__file__).resolve().parents[2] / "control-plane/tests/fixtures/documents"

FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
ORGANIZATION_ID = OrganizationID("org_golden")
NOTE_ID = NoteID("note-golden")
COMMAND_ID = CommandID("command-golden")
EVENT_ID = EventID("event-golden")
AUDIT_EVENT_ID = AuditEventID("audit-golden")
ACTOR = AuditActor(
    actor_type=AuditActorType.USER,
    actor_id="user_golden",
    actor_email="golden@example.com",
    actor_role="admin",
    impersonated_by=None,
)
CLOCK_MODULES = [
    "library.domain.commands.base.datetime",
    "control_plane.domain.events.base.datetime",
    "control_plane.domain.audit.event.datetime",
    "control_plane.infrastructure.audit.publisher.datetime",
]


class RecordingEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, OutboundMessage]] = []

    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]:
        self.published.extend((topic_name, message) for message in messages)
        return [str(index) for index in range(len(messages))]


@pytest.fixture(autouse=True)
def _golden_environment(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv("SERVICE", Service.NOTES)
    monkeypatch.delenv("FEATURE_ENVIRONMENT", raising=False)
    for module in CLOCK_MODULES:
        mocker.patch(module, wraps=datetime).now.return_value = FIXED_TIME
    mocker.patch("control_plane.domain.audit.event.AuditEventID", return_value=AUDIT_EVENT_ID)
    LocalDatabase.clear()
    set_cloud_provider(LOCAL_PROVIDER)
    token = init_audit_context()
    set_actor(ACTOR)
    set_source(AuditSource.REST)
    set_correlation_id("correlation-golden")
    set_causation_id("causation-golden")
    set_request_metadata(request_id="request-golden", ip_address="203.0.113.1", user_agent="golden-agent")
    yield
    flush_audit_context(token=token)
    reset_cloud_provider()
    LocalDatabase.clear()


def canonical(document: Any, /) -> bytes:
    return (json.dumps(to_jsonable_python(document), indent=2, sort_keys=True) + "\n").encode()


def golden(name: str, /) -> bytes:
    return canonical(json.loads((FIXTURES / f"{name}.json").read_text()))


def stored(collection: str, document_id: str, /) -> dict[str, Any]:
    document = LocalDatabase.read(collection_id=f"{Service.NOTES}_{collection}", document_id=document_id)
    assert document is not None
    return {key: value for key, value in document.data.items() if key != "_subcollection_metadata"}


async def emit_command() -> dict[str, Any]:
    async with unit_of_work():
        await CommandDispatcher().save(
            SummarizeNote(organization_id=ORGANIZATION_ID, note_id=NOTE_ID),
            organization_id=ORGANIZATION_ID,
            command_id=COMMAND_ID,
        )
    return stored("commands", COMMAND_ID)


async def emit_event() -> dict[str, Any]:
    async with unit_of_work():
        await EventPublisher().save(
            NoteCreated(organization_id=ORGANIZATION_ID, note_id=NOTE_ID),
            organization_id=ORGANIZATION_ID,
            event_id=EVENT_ID,
        )
    return stored("events", EVENT_ID)


async def emit_audit_event() -> dict[str, Any]:
    async with unit_of_work():
        await AuditEventPublisher().save(
            action=AuditAction.UPDATED,
            resource_type="Note",
            resource_id=NOTE_ID,
            organization_id=ORGANIZATION_ID,
            changes=[FieldChange(field="status", before="pending", after="summarizing", value_captured=True)],
        )
    return stored("audit", AUDIT_EVENT_ID)


async def emit_task() -> dict[str, Any]:
    command = CommandRead.model_validate(await emit_command())
    task_queue = LocalTaskQueue()
    await submit_command.handler(
        command=command,
        command_store=LOCAL_PROVIDER.document_store(
            collection="commands", model=CommandRead, partition_key_type=OrganizationID, service=Service.NOTES
        ),
        task_queue=task_queue,
        cache=FakeAsyncCache(),
        service=Service.NOTES,
    )
    (task,) = task_queue.enqueued
    return {
        "service": task.service,
        "task": task.task,
        "body": task.body,
        "params": task.params,
        "headers": task.headers,
    }


async def emit_outbound_message() -> dict[str, Any]:
    event = EventRead.model_validate(await emit_event())
    event_bus = RecordingEventBus()
    await publish_event.handler(
        event=event,
        event_bus=event_bus,
        event_store=LOCAL_PROVIDER.document_store(
            collection="events", model=EventRead, partition_key_type=OrganizationID, service=Service.NOTES
        ),
        cache=FakeAsyncCache(),
        service=Service.NOTES,
        topic_name=os.getenv("FEATURE_ENVIRONMENT", "") + "domain_events",
    )
    ((topic_name, message),) = event_bus.published
    return {"topic_name": topic_name, **message}


async def test_a_stored_command_matches_the_golden_document() -> None:
    assert canonical(await emit_command()) == golden("command")


async def test_a_stored_event_matches_the_golden_document() -> None:
    assert canonical(await emit_event()) == golden("event")


async def test_a_stored_audit_event_matches_the_golden_document() -> None:
    assert canonical(await emit_audit_event()) == golden("audit_event")


async def test_a_submitted_task_matches_the_golden_document() -> None:
    assert canonical(await emit_task()) == golden("task")


async def test_a_published_message_matches_the_golden_document() -> None:
    assert canonical(await emit_outbound_message()) == golden("outbound_message")


def test_the_fixed_timestamps_are_what_the_fixtures_say() -> None:
    assert to_jsonable_python(FIXED_TIME) == "2026-01-02T03:04:05Z"
    assert to_jsonable_python(FIXED_TIME + timedelta(days=1)) == "2026-01-03T03:04:05Z"
