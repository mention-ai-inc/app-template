import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from control_plane.application.ports.documents import DocumentID, IDocumentStore
from control_plane.application.ports.eventbus import IEventBus, OutboundMessage
from control_plane.application.ports.transactions import ITransaction
from control_plane.domain.events.base import EventRead
from control_plane.domain.value_objects.common import Service
from control_plane.domain.value_objects.users import UserID
from control_plane.infrastructure.persistence.cache.base import AsyncCache, get_global_cache_key
from control_plane.logs import SIMPLE_LOGGER_NAME
from control_plane.presentation.api.app import trigger
from control_plane.presentation.dependencies import get_event_bus
from control_plane.providers.registry import get_cloud_provider

DOMAIN_EVENTS_TOPIC = os.getenv("FEATURE_ENVIRONMENT", "") + "domain_events"
CACHE_TTL = 30

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def get_event_store() -> IDocumentStore[EventRead, UserID, ITransaction]:
    return get_cloud_provider().document_store(collection="events", model=EventRead, partition_key_type=UserID)


@trigger
async def publish_event(
    event: Annotated[EventRead | None, Depends(get_cloud_provider().change_feed(EventRead))],
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    event_store: Annotated[IDocumentStore[EventRead, UserID, ITransaction], Depends(get_event_store)],
    cache: Annotated[AsyncCache, Depends()],
    service: Annotated[Service, Depends(lambda: os.getenv("SERVICE", ""))],
    topic_name: Annotated[str, Depends(lambda: os.getenv("FEATURE_ENVIRONMENT", "") + "domain_events")],
) -> None:
    if event is None or event.published_at is not None:
        return

    cache_key = get_global_cache_key(component="event_publisher", service=service, name=event.id)
    is_new = await cache.set(cache_key, b"1", nx=True, ex=CACHE_TTL)

    if not is_new:
        return

    message: OutboundMessage = {
        "data": json.dumps(event.payload, default=str),
        "attributes": {
            "service": service,
            "event": event.name,
            "event_id": event.id,
            "organization_id": event.organization_id or "",
            "actor": event.actor.model_dump_json() if event.actor is not None else "",
            "correlation_id": event.correlation_id or event.id,
            "causation_id": event.id,
        },
    }
    await event_bus.publish(topic_name=topic_name, messages=[message])
    await event_store.field_set(document_id=DocumentID(event.id), field="published_at", value=datetime.now(UTC))
