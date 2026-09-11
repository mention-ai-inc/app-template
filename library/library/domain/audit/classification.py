from pydantic import BaseModel


class _AuditClassification:
    def __init__(self, name: str, /) -> None:
        self._name = name

    def __repr__(self) -> str:
        return f"AuditClassification({self._name})"


AuditByValue = _AuditClassification("by_value")
AuditExcluded = _AuditClassification("excluded")


def by_value_fields(model: type[BaseModel], /) -> set[str]:
    return __marked_fields(model, AuditByValue)


def excluded_fields(model: type[BaseModel], /) -> set[str]:
    return __marked_fields(model, AuditExcluded)


def __marked_fields(model: type[BaseModel], marker: _AuditClassification, /) -> set[str]:
    return {name for name, field in model.model_fields.items() if any(item is marker for item in field.metadata)}
