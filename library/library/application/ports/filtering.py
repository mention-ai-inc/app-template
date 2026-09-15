from datetime import datetime
from typing import Any, cast

from library.application.ports.documents import Primitive, QueryFilter


def matches(value: Any, query_filter: QueryFilter, /) -> bool:
    expected = query_filter.value
    match query_filter.operator:
        case "==":
            return bool(value == expected)
        case "!=":
            return bool(value != expected)
        case ">":
            return comparable(value) and comparable(expected) and value > expected
        case ">=":
            return comparable(value) and comparable(expected) and value >= expected
        case "<":
            return comparable(value) and comparable(expected) and value < expected
        case "<=":
            return comparable(value) and comparable(expected) and value <= expected
        case "array_contains":
            return isinstance(value, list) and expected in cast(list[Any], value)
        case "in":
            return isinstance(expected, list) and value in cast(list[Any], expected)
        case "not_in":
            return isinstance(expected, list) and value not in cast(list[Any], expected)


def comparable(value: Any, /) -> bool:
    return isinstance(value, (int, float, str, datetime)) and not isinstance(value, bool)


def sort_key(value: Any, /) -> tuple[int, str]:
    if value is None:
        return (0, "")
    if isinstance(value, datetime):
        return (1, value.isoformat())
    if isinstance(value, bool):
        return (1, str(int(value)))
    if isinstance(value, (int, float)):
        return (1, f"{value:030.10f}")
    return (1, str(value))


def after(value: Any, cursor_value: Primitive, /) -> bool:
    return sort_key(value) > sort_key(cursor_value)
