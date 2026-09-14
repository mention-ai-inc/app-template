from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, NewType, Protocol, Self

from pydantic import BaseModel

from library.application.ports.transactions import ITransaction
from library.domain.entities import IEntity
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject

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


class IDocumentStore[
    EntityT: IEntity[Any],
    PartitionKeyT: IDValueObject | StringValueObject,
    TransactionT: ITransaction,
](Protocol):
    @classmethod
    def to_document_id(cls, entity_id: str | int | ModelValueObject, /) -> DocumentID: ...

    def connect_to_partition(self, partition_key: PartitionKeyT, /) -> AbstractContextManager[Self]: ...

    @property
    def collection_id(self) -> str: ...

    @property
    def active_partition_key(self) -> PartitionKeyT: ...

    async def get(self, *, document_id: DocumentID, uow: TransactionT | None = None) -> EntityT: ...

    async def get_many(
        self, *, document_ids: list[DocumentID], uow: TransactionT | None = None, ignore_missing: bool = False
    ) -> list[EntityT]: ...

    async def set(
        self, *, document_id: DocumentID, document_data: EntityT, uow: TransactionT | None = None
    ) -> None: ...

    async def update_fields(
        self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate], uow: TransactionT
    ) -> None: ...

    async def field_set(self, *, document_id: DocumentID, field: str, value: Primitive) -> None: ...

    async def mutate_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate]) -> None: ...

    async def set_merge(self, *, document_id: DocumentID, document_data: dict[str, Any]) -> None: ...

    async def delete(self, *, document_id: DocumentID, uow: TransactionT | None = None) -> None: ...

    async def query(
        self,
        *,
        mode: Literal["shallow", "deep"] = "shallow",
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: TransactionT | None = None,
    ) -> QueryResult[EntityT]: ...

    async def count(self, *, filters: list[QueryFilter] | None = None) -> int: ...

    async def query_ids(
        self,
        *,
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: TransactionT | None = None,
    ) -> list[DocumentID]: ...

    async def query_one(self, *, filters: list[QueryFilter], uow: TransactionT | None = None) -> EntityT | None: ...

    async def exists(self, *, document_id: DocumentID) -> bool: ...
