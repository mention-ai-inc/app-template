from collections.abc import Mapping
from typing import Any, cast

from library.application.ports.documents import (
    ArrayRemove,
    ArrayUnion,
    FieldUpdate,
    Increment,
    Primitive,
    QueryFilter,
    SortBy,
)
from library.application.ports.filtering import matches, sort_key


def matches_every_filter(document: dict[str, Any], filters: list[QueryFilter], /) -> bool:
    return all(matches(document.get(query_filter.field), query_filter) for query_filter in filters)


def is_after_cursor(document: dict[str, Any], cursor: dict[str, Primitive], /) -> bool:
    return all(sort_key(document.get(field)) > sort_key(value) for field, value in cursor.items())


def sort_documents[DocumentT: dict[str, Any]](documents: list[DocumentT], sort_by: SortBy | None, /) -> list[DocumentT]:
    if sort_by is None:
        return documents
    return sorted(
        documents, key=lambda document: sort_key(document.get(sort_by.field)), reverse=sort_by.direction == "DESCENDING"
    )


def apply_field_updates(document: dict[str, Any], field_updates: Mapping[str, FieldUpdate], /) -> dict[str, Any]:
    updated = dict(document)
    for name, update in field_updates.items():
        if isinstance(update, Increment):
            updated[name] = as_number(updated.get(name)) + update.value
        elif isinstance(update, ArrayUnion):
            existing = list(cast(list[Any], updated.get(name, [])))
            updated[name] = existing + [value for value in update.values if value not in existing]
        elif isinstance(update, ArrayRemove):
            existing = list(cast(list[Any], updated.get(name, [])))
            updated[name] = [value for value in existing if value not in update.values]
        else:
            updated[name] = update
    return updated


def as_number(value: Any, /) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return value
