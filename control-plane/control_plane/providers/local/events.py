from datetime import datetime

from pydantic import BaseModel

from control_plane.application.events import MessageParser
from control_plane.application.ports.eventbus import InboundEvent
from control_plane.domain.events.base import EventPayload


class LocalMessage(BaseModel):
    data: str
    attributes: dict[str, str]
    message_id: str
    publish_time: datetime


class LocalMessageParser[DataT: EventPayload](MessageParser[DataT]):
    async def __call__(self, message: LocalMessage) -> InboundEvent[DataT]:
        return await self.parse(
            encoded_data=message.data,
            raw_attributes=message.attributes,
            message_id=message.message_id,
            publish_time=message.publish_time,
        )
