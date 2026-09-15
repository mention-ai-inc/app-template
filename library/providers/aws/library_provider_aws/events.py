from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from library.application.events import MessageParser
from library.application.ports.eventbus import InboundEvent
from library.domain.events.base import EventPayload


class SnsMessageAttribute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    value: str = Field(alias="Value")


class SnsNotification(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(alias="MessageId")
    message: str = Field(alias="Message")
    timestamp: datetime = Field(alias="Timestamp")
    topic_arn: str | None = Field(alias="TopicArn", default=None)
    attributes: dict[str, SnsMessageAttribute] = Field(alias="MessageAttributes", default_factory=dict)


class SnsMessageParser[DataT: EventPayload](MessageParser[DataT]):
    async def __call__(self, message: SnsNotification) -> InboundEvent[DataT]:
        return await self.parse(
            encoded_data=message.message,
            raw_attributes={name: attribute.value for name, attribute in message.attributes.items()},
            message_id=message.message_id,
            publish_time=message.timestamp,
        )
