import logging
from datetime import datetime
from typing import Any

import proto
from cloudevents.v1.http import from_http
from fastapi import Request
from google.events.cloud.firestore import DocumentEventData
from pydantic import BaseModel, ValidationError

from library.logs import SIMPLE_LOGGER_NAME


class FirestoreDocument[DataT: BaseModel]:
    def __init__(self, data_model: type[DataT], /) -> None:
        self._data_model = data_model
        self._logger = logging.getLogger(SIMPLE_LOGGER_NAME)

    async def __call__(self, request: Request) -> DataT | None:
        body = await request.body()
        headers = dict(request.headers)
        cloud_event = from_http(headers, body)

        event_data: bytes = cloud_event.data
        payload = DocumentEventData()
        payload._pb.ParseFromString(event_data)

        raw_document = proto.Message.to_dict(payload.value)["fields"]
        document = self.__unwrap_firestore_document(document=raw_document)

        try:
            return self._data_model.model_validate(document)
        except ValidationError as error:
            self._logger.error(f"Validation error: {error}")
            return

    def __unwrap_firestore_document(self, *, document: dict[str, Any]) -> dict[str, Any]:
        def _unwrap_value(value: Any) -> Any:
            if not isinstance(value, dict):
                return value

            if "string_value" in value:
                return value["string_value"]
            elif "integer_value" in value:
                return int(value["integer_value"])  # type: ignore
            elif "boolean_value" in value:
                return value["boolean_value"]
            elif "timestamp_value" in value:
                return datetime.fromisoformat(value["timestamp_value"])  # type: ignore
            elif "null_value" in value:
                return None
            elif "double_value" in value:
                return float(value["double_value"])  # type: ignore
            elif "map_value" in value and "fields" in value["map_value"]:
                return {key: _unwrap_value(val) for key, val in value["map_value"]["fields"].items()}
            elif "array_value" in value and "values" in value["array_value"]:
                return [_unwrap_value(val) for val in value["array_value"]["values"]]
            else:
                return {key: _unwrap_value(val) for key, val in value.items()}

        return {key: _unwrap_value(val) for key, val in document.items()}
