import base64
import uuid
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class StringValueObject(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))

    def __new__(cls, value: str | bytes, /) -> Self:
        if isinstance(value, bytes):
            value = value.decode()
        return super().__new__(cls, value)


class IntegerValueObject(int):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(int))

    def __new__(cls, value: int, /) -> Self:
        return super().__new__(cls, value)


class IDValueObject(str):
    PREFIX = ""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))

    @classmethod
    def from_json(cls, json_value: str, /) -> Self:
        u5 = uuid.uuid5(uuid.NAMESPACE_URL, json_value)
        return cls(cls.PREFIX + str(u5).replace("-", ""))

    def __new__(cls, raw_value: str | uuid.UUID | None = None, /) -> Self:
        if raw_value is None:
            value = uuid.uuid4().hex
        elif isinstance(raw_value, uuid.UUID):
            value = raw_value.hex
        elif not raw_value.startswith(cls.PREFIX):
            raise ValueError(f"Invalid ID: {raw_value}. These IDs must be prefixed with {cls.PREFIX}.")
        else:
            value = raw_value

        return super().__new__(cls, "".join([cls.PREFIX, value.removeprefix(cls.PREFIX)]))


class BlobValueObject(bytes):
    PLACEHOLDER_PREFIX = b"__BLOB__"

    @classmethod
    def is_placeholder(cls, value: bytes) -> bool:
        return value.startswith(cls.PLACEHOLDER_PREFIX)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(bytes))


class EnumValueObject(StrEnum):
    pass


class DictValueObject[K: str, V](dict[K, V]):
    pass


class ModelValueObject(BaseModel):
    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_id(cls, *, id: str) -> Self:
        json_str = base64.urlsafe_b64decode(id.encode()).decode()
        return cls.model_validate_json(json_str)

    def to_id(self) -> str:
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode()
