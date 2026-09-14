import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from library.application.triggers import FirestoreDocument
from library.domain.events.base import EventRead
from library.domain.value_objects.common import Service
from library.domain.value_objects.users import UserID
from library.infrastructure.cloud.pubsub import Message, Pubsub
from library.infrastructure.persistence.cache.base import AsyncCache, get_global_cache_key
from library.infrastructure.persistence.firestore import DocumentID, Firestore
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.api.app import trigger

DOMAIN_EVENTS_TOPIC = os.getenv("FEATURE_ENVIRONMENT", "") + "domain_events"
CACHE_TTL = 30

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def get_event_store() -> Firestore[EventRead, UserID]:
    return Firestore(collection="events", model=EventRead, partition_key_type=UserID)


@trigger
async def publish_event(
    event: Annotated[EventRead | None, Depends(FirestoreDocument(EventRead))],
    pubsub: Annotated[Pubsub, Depends()],
    event_store: Annotated[Firestore[EventRead, UserID], Depends(get_event_store)],
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

    message: Message = {
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
    await pubsub.publish(topic_name=topic_name, messages=[message])
    await event_store.field_set(document_id=DocumentID(event.id), field="published_at", value=datetime.now(UTC))
