from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

AttributeValue = dict[str, Any]

_serializer = TypeSerializer()
_deserializer = TypeDeserializer()


def to_attribute_value(value: Any, /) -> AttributeValue:
    serialized: AttributeValue = _serializer.serialize(to_storable(value))
    return serialized


def from_attribute_value(attribute_value: AttributeValue, /) -> Any:
    return from_storable(_deserializer.deserialize(attribute_value))


def to_item(document: Mapping[str, Any], /) -> dict[str, AttributeValue]:
    return {name: to_attribute_value(value) for name, value in document.items()}


def from_item(item: Mapping[str, AttributeValue], /) -> dict[str, Any]:
    return {name: from_attribute_value(attribute_value) for name, attribute_value in item.items()}


def to_storable(value: Any, /) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int, bytes)):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, Decimal):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return to_storable(value.value)
    if isinstance(value, Mapping):
        return {str(key): to_storable(item) for key, item in cast(Mapping[Any, Any], value).items()}
    if isinstance(value, Sequence):
        return [to_storable(item) for item in cast(Sequence[Any], value)]
    return str(value)


def from_storable(value: Any, /) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int, bytes)):
        return value
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, Mapping):
        return {str(key): from_storable(item) for key, item in cast(Mapping[Any, Any], value).items()}
    if isinstance(value, (list, tuple, set)):
        return [from_storable(item) for item in cast(Sequence[Any], value)]
    return value
