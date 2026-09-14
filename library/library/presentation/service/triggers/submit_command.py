import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends

from library.application.ports.documents import DocumentID
from library.application.triggers import FirestoreDocument
from library.domain.commands.base import CommandRead
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import UserID
from library.infrastructure.cloud.tasks import Tasks
from library.infrastructure.persistence.cache.base import AsyncCache, get_global_cache_key
from library.infrastructure.persistence.firestore import Firestore
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.api.app import trigger

CACHE_TTL = 30

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def get_command_store() -> Firestore[CommandRead, UserID]:
    return Firestore(collection="commands", model=CommandRead, partition_key_type=UserID)


@trigger
async def submit_command(
    command: Annotated[CommandRead | None, Depends(FirestoreDocument(CommandRead))],
    command_store: Annotated[Firestore[CommandRead, UserID], Depends(get_command_store)],
    tasks: Annotated[Tasks, Depends()],
    cache: Annotated[AsyncCache, Depends()],
    service: Annotated[Service, Depends(lambda: os.getenv("SERVICE", ""))],
) -> None:
    if command is None or command.dispatched_at is not None:
        return

    cache_key = get_global_cache_key(component="command_submitter", service=service, name=command.id)
    is_new = await cache.set(cache_key, b"1", nx=True, ex=CACHE_TTL)
    if not is_new:
        return

    headers = {"x-invoking-service": service, **_audit_headers(command)}

    if command.delay_seconds > 0:
        scheduled_time = datetime.now(UTC) + timedelta(seconds=command.delay_seconds)
        await tasks.add_task(
            service=command.service,
            task=command.executor_name,
            body=command.payload,
            scheduled_time=scheduled_time,
            params={"command_id": command.id},
            headers=headers,
        )
    else:
        await tasks.add_task(
            service=command.service,
            task=command.executor_name,
            body=command.payload,
            params={"command_id": command.id},
            headers=headers,
        )

    await command_store.field_set(document_id=DocumentID(command.id), field="dispatched_at", value=datetime.now(UTC))


def _audit_headers(command: CommandRead) -> dict[str, str]:
    headers = {
        "x-audit-correlation-id": command.correlation_id or command.id,
        "x-audit-causation-id": command.id,
    }
    if command.actor is not None:
        headers["x-audit-actor"] = command.actor.model_dump_json()
    return headers
