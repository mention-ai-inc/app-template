import logging
from typing import Any, cast

from fastapi import Request
from pydantic import BaseModel, ValidationError

from library.logs import SIMPLE_LOGGER_NAME
from library_provider_aws.dynamodb import INTERNAL_ATTRIBUTES
from library_provider_aws.serialization import from_attribute_value

NEW_IMAGE_FIELD = "NewImage"
OLD_IMAGE_FIELD = "OldImage"
STREAM_FIELD = "dynamodb"
RECORDS_FIELD = "Records"


class DynamoDbStreamRecord[DataT: BaseModel]:
    def __init__(self, data_model: type[DataT], /) -> None:
        self._data_model = data_model
        self._logger = logging.getLogger(SIMPLE_LOGGER_NAME)

    async def __call__(self, request: Request) -> DataT | None:
        try:
            payload = await request.json()
        except ValueError:
            return None

        image = self.__new_image(payload)
        if image is None:
            return None

        document = {
            name: from_attribute_value(attribute_value)
            for name, attribute_value in image.items()
            if name not in INTERNAL_ATTRIBUTES
        }

        try:
            return self._data_model.model_validate(document)
        except ValidationError as error:
            self._logger.error(f"Validation error: {error}")
            return None

    def __new_image(self, payload: Any, /) -> dict[str, Any] | None:
        record = self.__first_record(payload)
        if not isinstance(record, dict):
            return None

        stream = record.get(STREAM_FIELD, record)
        if not isinstance(stream, dict):
            return None

        image = stream.get(NEW_IMAGE_FIELD)
        return image if isinstance(image, dict) else None

    def __first_record(self, payload: Any, /) -> Any:
        if isinstance(payload, list):
            batch = cast(list[Any], payload)
            return batch[0] if len(batch) > 0 else None
        if isinstance(payload, dict) and RECORDS_FIELD in payload:
            records = cast(Any, payload[RECORDS_FIELD])
            if not isinstance(records, list):
                return None
            listed = cast(list[Any], records)
            return listed[0] if len(listed) > 0 else None
        return payload
