import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self, cast

from azure.servicebus import ServiceBusReceivedMessage
from azure.servicebus.aio import ServiceBusReceiver


@dataclass
class FakeMessage:
    body: str = "{}"
    application_properties: dict[str, str] = field(default_factory=dict[str, str])
    message_id: str = "message-1"
    enqueued_time_utc: datetime = datetime(2026, 1, 1, tzinfo=UTC)
    delivery_count: int = 1

    def as_received(self) -> ServiceBusReceivedMessage:
        return cast(ServiceBusReceivedMessage, self)


@dataclass
class FakeReceiver:
    messages: list[FakeMessage]
    on_empty: Callable[[], None] | None = None
    completed: list[FakeMessage] = field(default_factory=list[FakeMessage])
    abandoned: list[FakeMessage] = field(default_factory=list[FakeMessage])
    drained: bool = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def receive_messages(self, *, max_message_count: int, max_wait_time: int) -> list[Any]:  # noqa: ARG002
        await asyncio.sleep(0.01)
        if self.messages:
            return [self.messages.pop(0)]
        if not self.drained:
            self.drained = True
            if self.on_empty is not None:
                self.on_empty()
        return []

    async def complete_message(self, message: Any) -> None:
        self.completed.append(message)

    async def abandon_message(self, message: Any) -> None:
        self.abandoned.append(message)

    def as_receiver(self) -> ServiceBusReceiver:
        return cast(ServiceBusReceiver, self)


@dataclass
class FakeServiceBusClient:
    receivers: dict[str, FakeReceiver]
    requested_queues: list[str] = field(default_factory=list[str])
    requested_subscriptions: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])

    def get_queue_receiver(self, *, queue_name: str, sub_queue: Any = None) -> Any:  # noqa: ARG002
        self.requested_queues.append(queue_name)
        return self.receivers[queue_name]

    def get_subscription_receiver(
        self,
        *,
        topic_name: str,
        subscription_name: str,
        sub_queue: Any = None,  # noqa: ARG002
    ) -> Any:
        self.requested_subscriptions.append((topic_name, subscription_name))
        return self.receivers[subscription_name]


class FakeLockRenewer:
    def __init__(self, *_: object, **__: object) -> None:
        self.registered: list[Any] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def register(self, _receiver: Any, message: Any, **__: object) -> None:
        self.registered.append(message)


@dataclass
class FakeSender:
    sent: list[Any] = field(default_factory=list[Any])

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def send_messages(self, messages: Any) -> None:
        if isinstance(messages, list):
            self.sent.extend(cast(list[Any], messages))
        else:
            self.sent.append(messages)


@dataclass
class FakeSendingClient:
    sender: FakeSender
    topics: list[str] = field(default_factory=list[str])
    queues: list[str] = field(default_factory=list[str])

    def get_topic_sender(self, *, topic_name: str) -> FakeSender:
        self.topics.append(topic_name)
        return self.sender

    def get_queue_sender(self, *, queue_name: str) -> FakeSender:
        self.queues.append(queue_name)
        return self.sender
