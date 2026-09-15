from datetime import datetime

from pydantic import BaseModel

from library.application.events import MessageParser
from library.application.ports.eventbus import InboundEvent
from library.domain.events.base import EventPayload


class PubSubMessageBody(BaseModel):
    data: str
    attributes: dict[str, str]
    message_id: str
    publish_time: datetime


class PubSubMessage(BaseModel):
    message: PubSubMessageBody
    subscription: str | None = None


class PubSubMessageParser[DataT: EventPayload](MessageParser[DataT]):
    async def __call__(self, message: PubSubMessage) -> InboundEvent[DataT]:
        return await self.parse(
            encoded_data=message.message.data,
            raw_attributes=message.message.attributes,
            message_id=message.message.message_id,
            publish_time=message.message.publish_time,
        )
