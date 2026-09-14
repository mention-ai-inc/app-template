import base64
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from library.application.ports.eventbus import OutboundMessage


@dataclass
class PublishedMessage:
    topic_name: str
    data: str
    attributes: dict[str, str]
    message_id: str


@dataclass
class EnqueuedTask:
    service: str
    task: str
    body: dict[str, Any]
    params: dict[str, str] | None
    headers: dict[str, str] | None
    scheduled_time: datetime | None


class LocalEventBus:
    published: list[PublishedMessage] = []

    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]:
        message_ids: list[str] = []
        for message in messages:
            message_id = uuid.uuid4().hex
            type(self).published.append(
                PublishedMessage(
                    topic_name=topic_name,
                    data=base64.b64encode(message.get("data", "").encode()).decode(),
                    attributes=message.get("attributes", {}),
                    message_id=message_id,
                )
            )
            message_ids.append(message_id)
        return message_ids

    @classmethod
    def clear(cls) -> None:
        cls.published = []


@dataclass
class LocalTaskQueue:
    enqueued: list[EnqueuedTask] = field(default_factory=list[EnqueuedTask])

    def get_url(self, *, service: str, task: str, params: dict[str, str] | None = None) -> str:
        query = "" if params is None else "?" + "&".join(f"{key}={value}" for key, value in params.items())
        return f"local://{service}/commands/{task}{query}"

    async def add_task(
        self,
        *,
        service: str,
        task: str,
        body: dict[str, Any],
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        scheduled_time: datetime | None = None,
    ) -> None:
        self.enqueued.append(
            EnqueuedTask(
                service=service,
                task=task,
                body=body,
                params=params,
                headers=headers,
                scheduled_time=scheduled_time,
            )
        )
