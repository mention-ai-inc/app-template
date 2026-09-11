import base64
from datetime import datetime

from pydantic import BaseModel, ValidationError

from library.application.cache import IAsyncCache, get_global_cache_key
from library.application.errors import ApplicationError, ApplicationErrorType
from library.domain.events.base import EventPayload


class PubSubMessageMessage(BaseModel):
    data: str
    attributes: dict[str, str]
    message_id: str
    publish_time: datetime


class PubSubMessage(BaseModel):
    message: PubSubMessageMessage
    subscription: str | None = None


class EventAttributes(BaseModel):
    event: str
    service: str
    event_id: str | None = None


class PubSubEvent[DataT: BaseModel](BaseModel):
    data: DataT
    attributes: EventAttributes
    message_id: str
    publish_time: datetime


class MessageParser[DataT: EventPayload]:
    def __init__(
        self,
        *,
        data_models: list[type[DataT]],
        cache: IAsyncCache,
        deduplication_ttl_ms: int | None = None,
    ) -> None:
        models_by_event_name: dict[str, type[DataT]] = {}
        for data_model in data_models:
            models_by_event_name[data_model.pubsub_event_name()] = data_model

        self._data_models_by_event_name = models_by_event_name
        self._deduplication_ttl_ms = deduplication_ttl_ms
        self._cache = cache

    async def __call__(self, message: PubSubMessage) -> PubSubEvent[DataT]:
        json_data = base64.b64decode(message.message.data).decode()
        attributes = EventAttributes.model_validate(message.message.attributes)

        if self._deduplication_ttl_ms is not None and attributes.event_id is not None:
            cache_key = get_global_cache_key(component="message_parser", name=attributes.event_id)
            ttl_seconds = self._deduplication_ttl_ms // 1000
            is_new = await self._cache.set(cache_key, b"1", nx=True, ex=ttl_seconds)

            if not is_new:
                raise ApplicationError(
                    error_type=ApplicationErrorType.PROCESS_FAILED,
                    message=f"Duplicate message detected. Event ID: {attributes.event_id}",
                    public_message="Message already processed",
                )

        data_model = self._data_models_by_event_name.get(attributes.event)
        if data_model is None:
            raise ApplicationError(
                error_type=ApplicationErrorType.VALIDATION_ERROR,
                message=(
                    f"Event {attributes.event!r} is not handled by this listener. "
                    f"Expected one of: {sorted(self._data_models_by_event_name)}"
                ),
                public_message="Invalid event data",
            )

        try:
            parsed_data = data_model.model_validate_json(json_data)
        except ValidationError as error:
            raise ApplicationError(
                error_type=ApplicationErrorType.VALIDATION_ERROR,
                message=f"Message data failed validation for {data_model.__name__}: {error}. Message: {json_data}",
                public_message="Invalid event data",
            ) from error

        return PubSubEvent(
            data=parsed_data,
            attributes=attributes,
            message_id=message.message.message_id,
            publish_time=message.message.publish_time,
        )
