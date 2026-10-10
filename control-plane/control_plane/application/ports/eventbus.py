from datetime import datetime
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel


class OutboundMessage(TypedDict, total=False):
    data: str
    attributes: dict[str, str]


class EventAttributes(BaseModel):
    event: str
    service: str
    event_id: str | None = None


class InboundEvent[DataT: BaseModel](BaseModel):
    data: DataT
    attributes: EventAttributes
    message_id: str
    publish_time: datetime


class IEventBus(Protocol):
    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]: ...


class IMessageParser[DataT: BaseModel](Protocol):
    async def __call__(self, message: Any) -> InboundEvent[DataT]: ...
