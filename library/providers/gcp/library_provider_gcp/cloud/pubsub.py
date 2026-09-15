import base64
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, field_validator

from library.application.ports.eventbus import OutboundMessage
from library_provider_gcp.cloud.base import AuthenticatedClient, raise_for_status
from library_provider_gcp.cloud.project import get_project_id


class Message(TypedDict, total=False):
    data: str
    attributes: dict[str, str]
    messageId: str
    publishTime: str
    orderingKey: str


class Schema(BaseModel):
    schema_: str = Field(..., validation_alias="schema")
    encoding: Literal["ENCODING_UNSPECIFIED", "JSON", "BINARY"] = "JSON"


class Topic(BaseModel):
    name: str
    message_retention_duration: float | None = Field(default=None, validation_alias="messageRetentionDuration")
    schema_settings: Schema | None = Field(default=None, validation_alias="schemaSettings")

    @field_validator("message_retention_duration", mode="before")
    def message_retention_duration_to_float(cls, v: str) -> float:
        return float(v[:-1])


class PushConfig(BaseModel):
    push_endpoint: str | None = Field(default=None, validation_alias="pushEndpoint")
    attributes: dict[str, str] | None = Field(default=None, description="Endpoint configuration attributes.")


class DeadLetterPolicy(BaseModel):
    dead_letter_topic: str = Field(..., validation_alias="deadLetterTopic")
    max_delivery_attempts: int = Field(..., validation_alias="maxDeliveryAttempts")


class Subscription(BaseModel):
    name: str
    topic: str
    push_config: PushConfig | None = Field(default=None, validation_alias="pushConfig")
    ack_deadline_seconds: int = Field(default=10, validation_alias="ackDeadlineSeconds")
    retain_acked_messages: bool = Field(default=False, validation_alias="retainAckedMessages")
    message_retention_duration: float = Field(default=604800.0, validation_alias="messageRetentionDuration")
    enable_message_ordering: bool = Field(default=False, validation_alias="enableMessageOrdering")
    filter_: str | None = Field(default=None, validation_alias="filter")
    dead_letter_policy: DeadLetterPolicy | None = Field(default=None, validation_alias="deadLetterPolicy")

    @field_validator("message_retention_duration", mode="before")
    def message_retention_duration_to_float(cls, v: str) -> float:
        return float(v[:-1])


class ReceivedMessage(BaseModel):
    ack_id: str = Field(..., validation_alias="ackId")
    message: Message = Field(..., description="The message being received.")


class Pubsub:
    BASE_URL = "https://pubsub.googleapis.com/v1"

    def __init__(self, *, token: str | None = None) -> None:
        self._client: AuthenticatedClient | None = None
        self.token = token

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=self.BASE_URL, token=self.token)
        return self._client

    async def list_topics(self) -> list[Topic]:
        response = await self.client.get(f"/projects/{get_project_id()}/topics")
        raise_for_status(response)
        response_body = response.json()

        topics = [Topic.model_validate(topic) for topic in response_body["topics"]]
        return topics

    async def get_topic(self, *, topic_name: str) -> Topic:
        response = await self.client.get(f"/projects/{get_project_id()}/topics/{topic_name}")
        raise_for_status(response)
        response_body = response.json()

        topic = Topic.model_validate(response_body)
        return topic

    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]:
        for message in messages:
            if "data" in message:
                message["data"] = base64.b64encode(message["data"].encode()).decode()

        response = await self.client.post(
            f"/projects/{get_project_id()}/topics/{topic_name}:publish", json={"messages": messages}
        )
        raise_for_status(response)
        response_body = response.json()

        return response_body.get("messageIds", [])

    async def list_subscriptions(self) -> list[Subscription]:
        response = await self.client.get(f"/projects/{get_project_id()}/subscriptions")
        raise_for_status(response)
        response_body = response.json()

        subscriptions = [
            Subscription.model_validate(subscription) for subscription in response_body.get("subscriptions", [])
        ]
        return subscriptions

    async def get_subscription(self, *, subscription_name: str) -> Subscription:
        response = await self.client.get(f"/projects/{get_project_id()}/subscriptions/{subscription_name}")
        raise_for_status(response)
        response_body = response.json()

        subscription = Subscription.model_validate(response_body)
        return subscription

    async def pull_messages(self, *, subscription_name: str, max_messages: int = 1) -> list[ReceivedMessage]:
        response = await self.client.post(
            f"/projects/{get_project_id()}/subscriptions/{subscription_name}:pull", json={"maxMessages": max_messages}
        )
        raise_for_status(response)
        response_body = response.json()

        messages = [ReceivedMessage.model_validate(message) for message in response_body.get("receivedMessages", [])]
        return messages

    async def acknowledge_messages(self, *, subscription_name: str, ack_ids: list[str]) -> None:
        response = await self.client.post(
            f"/projects/{get_project_id()}/subscriptions/{subscription_name}:acknowledge", json={"ackIds": ack_ids}
        )
        raise_for_status(response)
