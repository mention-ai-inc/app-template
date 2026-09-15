import base64
from datetime import datetime

from pydantic import ValidationError

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.cache import IAsyncCache, get_global_cache_key
from library.application.ports.eventbus import EventAttributes, InboundEvent
from library.domain.events.base import EventPayload


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
            models_by_event_name[data_model.event_name()] = data_model

        self._data_models_by_event_name = models_by_event_name
        self._deduplication_ttl_ms = deduplication_ttl_ms
        self._cache = cache

    async def parse(
        self,
        *,
        encoded_data: str,
        raw_attributes: dict[str, str],
        message_id: str,
        publish_time: datetime,
    ) -> InboundEvent[DataT]:
        json_data = base64.b64decode(encoded_data).decode()
        attributes = EventAttributes.model_validate(raw_attributes)

        await self.__guard_duplicate(attributes)
        data_model = self.__route(attributes)

        try:
            parsed_data = data_model.model_validate_json(json_data)
        except ValidationError as error:
            raise ApplicationError(
                error_type=ApplicationErrorType.VALIDATION_ERROR,
                message=f"Message data failed validation for {data_model.__name__}: {error}. Message: {json_data}",
                public_message="Invalid event data",
            ) from error

        return InboundEvent(data=parsed_data, attributes=attributes, message_id=message_id, publish_time=publish_time)

    async def __guard_duplicate(self, attributes: EventAttributes, /) -> None:
        if self._deduplication_ttl_ms is None or attributes.event_id is None:
            return

        cache_key = get_global_cache_key(component="message_parser", name=attributes.event_id)
        is_new = await self._cache.set(cache_key, b"1", nx=True, ex=self._deduplication_ttl_ms // 1000)

        if not is_new:
            raise ApplicationError(
                error_type=ApplicationErrorType.PROCESS_FAILED,
                message=f"Duplicate message detected. Event ID: {attributes.event_id}",
                public_message="Message already processed",
            )

    def __route(self, attributes: EventAttributes, /) -> type[DataT]:
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
        return data_model
