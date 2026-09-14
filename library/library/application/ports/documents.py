from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, NewType

from pydantic import BaseModel

from library.domain.entities import IEntity

DocumentID = NewType("DocumentID", str)
Primitive = (
    bool | str | int | float | datetime | Sequence[str] | Sequence[int] | Sequence[float] | Sequence[datetime] | None
)
QueryOperator = Literal["==", "!=", ">", ">=", "<", "<=", "array_contains", "in", "not_in"]


@dataclass(frozen=True)
class Increment:
    value: int | float


@dataclass(frozen=True)
class ArrayUnion:
    values: Sequence[Any]


@dataclass(frozen=True)
class ArrayRemove:
    values: Sequence[Any]


FieldUpdate = Primitive | Increment | ArrayUnion | ArrayRemove


class QueryFilter(BaseModel):
    field: str
    operator: QueryOperator
    value: Primitive


class SortBy(BaseModel):
    field: str
    direction: Literal["ASCENDING", "DESCENDING"]


@dataclass
class QueryResult[EntityT: IEntity[Any]]:
    entities: list[EntityT]
    subcollection_counts: list[dict[str, int]]
    has_more: bool
