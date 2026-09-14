import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from library.application.ports.documents import DocumentID
from library.application.triggers import FirestoreDocument
from library.domain.audit.event import AuditEventRead
from library.domain.value_objects.users import UserID
from library.infrastructure.cloud.pubsub import Message, Pubsub
from library.infrastructure.persistence.cache.base import AsyncCache, get_global_cache_key
from library.infrastructure.persistence.firestore import Firestore
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.api.app import trigger

AUDIT_EVENTS_TOPIC = os.getenv("FEATURE_ENVIRONMENT", "") + "audit_events"
CACHE_TTL = 30

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def get_audit_event_store() -> Firestore[AuditEventRead, UserID]:
    return Firestore(collection="audit", model=AuditEventRead, partition_key_type=UserID)


@trigger
async def publish_audit_event(
    event: Annotated[AuditEventRead | None, Depends(FirestoreDocument(AuditEventRead))],
    pubsub: Annotated[Pubsub, Depends()],
    event_store: Annotated[Firestore[AuditEventRead, UserID], Depends(get_audit_event_store)],
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
    message: Message = {
        "data": json.dumps(event.payload, default=str),
        "attributes": {
            "service": service,
            "action": event.name,
            "actor_id": actor.get("actor_id") or "",
            "resource_type": event.payload.get("resource_type") or "",
            "organization_id": event.organization_id or "",
        },
    }
    await pubsub.publish(topic_name=topic_name, messages=[message])
    await event_store.field_set(document_id=DocumentID(event.id), field="published_at", value=datetime.now(UTC))
