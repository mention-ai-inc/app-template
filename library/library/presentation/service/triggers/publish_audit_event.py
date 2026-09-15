import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from library.application.ports.documents import DocumentID, IDocumentStore
from library.application.ports.eventbus import IEventBus, OutboundMessage
from library.application.ports.transactions import ITransaction
from library.domain.audit.event import AuditEventRead
from library.domain.value_objects.users import UserID
from library.infrastructure.persistence.cache.base import AsyncCache, get_global_cache_key
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.api.app import trigger
from library.presentation.dependencies import get_event_bus
from library.providers.registry import get_cloud_provider

AUDIT_EVENTS_TOPIC = os.getenv("FEATURE_ENVIRONMENT", "") + "audit_events"
CACHE_TTL = 30

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def get_audit_event_store() -> IDocumentStore[AuditEventRead, UserID, ITransaction]:
    return get_cloud_provider().document_store(collection="audit", model=AuditEventRead, partition_key_type=UserID)


@trigger
async def publish_audit_event(
    event: Annotated[AuditEventRead | None, Depends(get_cloud_provider().change_feed(AuditEventRead))],
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    event_store: Annotated[IDocumentStore[AuditEventRead, UserID, ITransaction], Depends(get_audit_event_store)],
    cache: Annotated[AsyncCache, Depends()],
    service: Annotated[str, Depends(lambda: os.getenv("SERVICE", ""))],
    topic_name: Annotated[str, Depends(lambda: os.getenv("FEATURE_ENVIRONMENT", "") + "audit_events")],
) -> None:
    if event is None or event.published_at is not None:
        return

    cache_key = get_global_cache_key(component="audit_event_publisher", service=service, name=event.id)
    is_new = await cache.set(cache_key, b"1", nx=True, ex=CACHE_TTL)

    if not is_new:
        return

    actor = event.payload.get("actor") or {}
    message: OutboundMessage = {
        "data": json.dumps(event.payload, default=str),
        "attributes": {
            "service": service,
            "action": event.name,
            "actor_id": actor.get("actor_id") or "",
            "resource_type": event.payload.get("resource_type") or "",
            "organization_id": event.organization_id or "",
        },
    }
    await event_bus.publish(topic_name=topic_name, messages=[message])
    await event_store.field_set(document_id=DocumentID(event.id), field="published_at", value=datetime.now(UTC))
