from typing import Any

from library.domain.aggregates import Aggregate
from library.domain.audit.change import FieldChange
from library.domain.audit.classification import by_value_fields, excluded_fields

__IDENTITY_FIELDS = {"id", "organization_id"}


def diff_aggregate(before: Aggregate[Any, Any, Any], after: Aggregate[Any, Any, Any], /) -> list[FieldChange]:
    model = type(after)
    by_value = by_value_fields(model)
    excluded = excluded_fields(model)
    before_dump = before.model_dump(mode="json")
    after_dump = after.model_dump(mode="json")

    changes: list[FieldChange] = []
    for field in model.model_fields:
        if field in __IDENTITY_FIELDS or field in excluded:
            continue

        old_value = before_dump.get(field)
        new_value = after_dump.get(field)
        if old_value == new_value:
            continue

        if field in by_value:
            changes.append(FieldChange(field=field, before=old_value, after=new_value, value_captured=True))
        else:
            changes.append(FieldChange(field=field, before=None, after=None, value_captured=False))

    return changes
