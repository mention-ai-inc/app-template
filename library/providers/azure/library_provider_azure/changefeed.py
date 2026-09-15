import logging
from typing import Any

from fastapi import Request
from pydantic import BaseModel, ValidationError

from library.logs import SIMPLE_LOGGER_NAME
from library_provider_azure.documents import to_record


class CosmosChangeFeedItem[DataT: BaseModel]:
    def __init__(self, data_model: type[DataT], /) -> None:
        self._data_model = data_model
        self._logger = logging.getLogger(SIMPLE_LOGGER_NAME)

    async def __call__(self, request: Request) -> DataT | None:
        item: dict[str, Any] = await request.json()

        try:
            return self._data_model.model_validate(to_record(item))
        except (ValidationError, KeyError) as error:
            self._logger.error(f"Validation error: {error}")
            return None
