import copy
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Literal, Self, cast

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.documents import (
    DocumentID,
    FieldUpdate,
    Primitive,
    QueryFilter,
    QueryResult,
    SortBy,
)
from library.domain.entities import IEntity
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.providers.local.database import BufferedWrite, LocalDatabase, LocalTransaction, apply_field_updates

SUBCOLLECTION_METADATA_FIELD = "_subcollection_metadata"
NoPartitionSelectedError = InfrastructureError(
    error_type=InfrastructureErrorType.QUERY_ERROR, message="Must select an Organization ID to use this collection"
)


class LocalDocumentStore[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject]:
    def __init__(
        self,
        *,
        collection: str,
        model: type[EntityT],
        partition_key_type: type[PartitionKeyT],
        service: Service | str | None = None,
        feature_environment: str | None = None,
    ) -> None:
        self._collection = collection
        self._model = model
        self._partition_key_type = partition_key_type
        self._active_partition_key: PartitionKeyT | None = None
        resolved_service = service if service is not None else ""
        self._service = resolved_service.value if isinstance(resolved_service, Service) else resolved_service
        self._feature_environment = feature_environment or ""
        self._collection_id = f"{self._feature_environment}{self._service}_{collection}"

    @classmethod
    def to_document_id(cls, entity_id: str | int | ModelValueObject, /) -> DocumentID:
        if isinstance(entity_id, ModelValueObject):
            return DocumentID(entity_id.to_id())
        return DocumentID(str(entity_id))

    @contextmanager
    def connect_to_partition(self, partition_key: PartitionKeyT, /) -> Generator[Self]:
        scoped = copy.copy(self)
        scoped._collection_id = f"{self._feature_environment}{self._service}_{partition_key}_{self._collection}"
        scoped._active_partition_key = partition_key
        yield scoped

    @property
    def collection_id(self) -> str:
        return self._collection_id

    @property
    def active_partition_key(self) -> PartitionKeyT:
        if self._active_partition_key is None:
            raise NoPartitionSelectedError
        return self._active_partition_key

    async def get(self, *, document_id: DocumentID, uow: LocalTransaction | None = None) -> EntityT:
        self.__guard_read(uow)
        stored = LocalDatabase.read(collection_id=self._collection_id, document_id=document_id)
        self.__record_read(uow, document_id=document_id)

        if stored is None:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"{self._collection_id} entity with ID {document_id} not found",
                public_message="The requested resource was not found",
            )

        return self._model.model_validate(self.__hydrate(document_id=document_id, root=stored.data, deep=True))

    async def get_many(
        self, *, document_ids: list[DocumentID], uow: LocalTransaction | None = None, ignore_missing: bool = False
    ) -> list[EntityT]:
        entities: list[EntityT] = []
        for document_id in document_ids:
            if (
                ignore_missing
                and LocalDatabase.read(collection_id=self._collection_id, document_id=document_id) is None
            ):
                continue
            entities.append(await self.get(document_id=document_id, uow=uow))
        return entities

    async def set(
        self, *, document_id: DocumentID, document_data: EntityT, uow: LocalTransaction | None = None
    ) -> None:
        subentity_names = self._model.get_subentity_names()
        record = document_data.model_dump(exclude=set(subentity_names))

        previous = LocalDatabase.read(collection_id=self._collection_id, document_id=document_id)
        previous_metadata: dict[str, list[str]] = (
            {} if previous is None else previous.data.get(SUBCOLLECTION_METADATA_FIELD, {})
        )

        metadata: dict[str, list[str]] = {}
        for subentity_name in subentity_names:
            metadata[subentity_name] = []
            subcollection_id = self.__subcollection_id(document_id=document_id, subentity_name=subentity_name)
            subentities = cast(list[IEntity[Any]], getattr(document_data, subentity_name))
            for subentity in subentities:
                subdocument_id = self.to_document_id(subentity.id)
                self.__write(uow, subcollection_id, subdocument_id, subentity.model_dump())
                metadata[subentity_name].append(subdocument_id)

            orphaned = set(previous_metadata.get(subentity_name, [])) - set(metadata[subentity_name])
            for orphaned_subdocument_id in sorted(orphaned):
                self.__delete(uow, subcollection_id, orphaned_subdocument_id)

        self.__write(uow, self._collection_id, document_id, {**record, SUBCOLLECTION_METADATA_FIELD: metadata})

    async def update_fields(
        self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate], uow: LocalTransaction
    ) -> None:
        uow.has_written = True
        uow.writes.append(
            BufferedWrite(
                collection_id=self._collection_id,
                document_id=document_id,
                operation="update",
                payload=dict(field_updates),
            )
        )

    async def field_set(self, *, document_id: DocumentID, field: str, value: Primitive) -> None:
        await self.mutate_fields(document_id=document_id, field_updates={field: value})

    async def mutate_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate]) -> None:
        stored = LocalDatabase.read(collection_id=self._collection_id, document_id=document_id)
        if stored is None:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"{self._collection_id} entity with ID {document_id} not found",
                public_message="The requested resource was not found",
            )
        LocalDatabase.write(
            collection_id=self._collection_id,
            document_id=document_id,
            data=apply_field_updates(stored.data, field_updates),
        )

    async def set_merge(self, *, document_id: DocumentID, document_data: dict[str, Any]) -> None:
        stored = LocalDatabase.read(collection_id=self._collection_id, document_id=document_id)
        merged = {**({} if stored is None else stored.data), **document_data}
        LocalDatabase.write(collection_id=self._collection_id, document_id=document_id, data=merged)

    async def delete(self, *, document_id: DocumentID, uow: LocalTransaction | None = None) -> None:
        stored = LocalDatabase.read(collection_id=self._collection_id, document_id=document_id)
        if stored is not None:
            metadata: dict[str, list[str]] = stored.data.get(SUBCOLLECTION_METADATA_FIELD, {})
            for subentity_name, subdocument_ids in metadata.items():
                subcollection_id = self.__subcollection_id(document_id=document_id, subentity_name=subentity_name)
                for subdocument_id in subdocument_ids:
                    self.__delete(uow, subcollection_id, subdocument_id)

        self.__delete(uow, self._collection_id, document_id)

    async def query(
        self,
        *,
        mode: Literal["shallow", "deep"] = "shallow",
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: LocalTransaction | None = None,
    ) -> QueryResult[EntityT]:
        self.__guard_read(uow)
        matches = self.__matching_documents(filters=filters, cursor=cursor, sort_by=sort_by)
        subentity_names = self._model.get_subentity_names()

        entities: list[EntityT] = []
        subcollection_counts: list[dict[str, int]] = []
        for document_id, stored in matches:
            self.__record_read(uow, document_id=document_id)
            metadata: dict[str, list[str]] = stored.data.get(SUBCOLLECTION_METADATA_FIELD, {})
            subcollection_counts.append({name: len(metadata.get(name, [])) for name in subentity_names})
            entities.append(
                self._model.model_validate(
                    self.__hydrate(document_id=document_id, root=stored.data, deep=mode == "deep")
                )
            )

        if limit is not None and len(entities) > limit:
            return QueryResult(
                entities=entities[:limit], subcollection_counts=subcollection_counts[:limit], has_more=True
            )

        return QueryResult(entities=entities, subcollection_counts=subcollection_counts, has_more=False)

    async def count(self, *, filters: list[QueryFilter] | None = None) -> int:
        return len(self.__matching_documents(filters=filters, cursor=None, sort_by=None))

    async def query_ids(
        self,
        *,
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: LocalTransaction | None = None,
    ) -> list[DocumentID]:
        self.__guard_read(uow)
        matches = self.__matching_documents(filters=filters, cursor=cursor, sort_by=sort_by)
        document_ids = [document_id for document_id, _ in matches]
        selected = document_ids if limit is None else document_ids[:limit]
        for document_id in selected:
            self.__record_read(uow, document_id=document_id)
        return selected

    async def query_one(self, *, filters: list[QueryFilter], uow: LocalTransaction | None = None) -> EntityT | None:
        results = await self.query(filters=filters, uow=uow)

        if len(results.entities) == 0:
            return None

        if len(results.entities) > 1:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.VALIDATION_ERROR,
                message="Multiple entities found for a query_one",
                public_message="Multiple resources were found",
            )

        return results.entities[0]

    async def exists(self, *, document_id: DocumentID) -> bool:
        return LocalDatabase.read(collection_id=self._collection_id, document_id=document_id) is not None

    def __subcollection_id(self, *, document_id: DocumentID, subentity_name: str) -> str:
        return f"{self._collection_id}/{document_id}/{subentity_name}"

    def __hydrate(self, *, document_id: DocumentID, root: dict[str, Any], deep: bool) -> dict[str, Any]:
        hydrated = copy.deepcopy(root)
        metadata: dict[str, list[str]] = hydrated.get(SUBCOLLECTION_METADATA_FIELD, {})
        for subentity_name in self._model.get_subentity_names():
            if not deep:
                hydrated[subentity_name] = []
                continue
            subcollection_id = self.__subcollection_id(document_id=document_id, subentity_name=subentity_name)
            hydrated[subentity_name] = [
                stored.data
                for stored in (
                    LocalDatabase.read(collection_id=subcollection_id, document_id=subdocument_id)
                    for subdocument_id in metadata.get(subentity_name, [])
                )
                if stored is not None
            ]
        return hydrated

    def __matching_documents(
        self, *, filters: list[QueryFilter] | None, cursor: dict[str, Primitive] | None, sort_by: SortBy | None
    ) -> list[tuple[DocumentID, Any]]:
        matches = [
            (DocumentID(document_id), stored)
            for document_id, stored in LocalDatabase.read_all(collection_id=self._collection_id).items()
            if all(_matches(stored.data.get(f.field), f) for f in filters or [])
        ]

        if sort_by is not None:
            matches.sort(
                key=lambda m: _sort_key(m[1].data.get(sort_by.field)), reverse=sort_by.direction == "DESCENDING"
            )
        else:
            matches.sort(key=lambda m: m[0])

        if cursor is not None:
            matches = [
                m for m in matches if all(_after(m[1].data.get(field), value) for field, value in cursor.items())
            ]

        return matches

    def __write(self, uow: LocalTransaction | None, collection_id: str, document_id: str, data: dict[str, Any]) -> None:
        if uow is None:
            LocalDatabase.write(collection_id=collection_id, document_id=document_id, data=data)
            return
        uow.has_written = True
        uow.writes.append(
            BufferedWrite(collection_id=collection_id, document_id=document_id, operation="set", payload=data)
        )

    def __delete(self, uow: LocalTransaction | None, collection_id: str, document_id: str) -> None:
        if uow is None:
            LocalDatabase.remove(collection_id=collection_id, document_id=document_id)
            return
        uow.has_written = True
        uow.writes.append(
            BufferedWrite(collection_id=collection_id, document_id=document_id, operation="delete", payload=None)
        )

    def __record_read(self, uow: LocalTransaction | None, *, document_id: DocumentID) -> None:
        if uow is None:
            return
        stored = LocalDatabase.read(collection_id=self._collection_id, document_id=document_id)
        uow.read_versions[(self._collection_id, document_id)] = 0 if stored is None else stored.version

    def __guard_read(self, uow: LocalTransaction | None) -> None:
        if uow is not None and uow.has_written:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=(
                    "Read after write inside a unit of work. Phase every read before the first write "
                    "(see .agents/rules/read-after-write.md)"
                ),
            )


def _matches(value: Any, query_filter: QueryFilter, /) -> bool:
    expected = query_filter.value
    match query_filter.operator:
        case "==":
            return bool(value == expected)
        case "!=":
            return bool(value != expected)
        case ">":
            return _comparable(value) and _comparable(expected) and value > expected
        case ">=":
            return _comparable(value) and _comparable(expected) and value >= expected
        case "<":
            return _comparable(value) and _comparable(expected) and value < expected
        case "<=":
            return _comparable(value) and _comparable(expected) and value <= expected
        case "array_contains":
            return isinstance(value, list) and expected in cast(list[Any], value)
        case "in":
            return isinstance(expected, list) and value in cast(list[Any], expected)
        case "not_in":
            return isinstance(expected, list) and value not in cast(list[Any], expected)


def _comparable(value: Any, /) -> bool:
    return isinstance(value, (int, float, str, datetime)) and not isinstance(value, bool)


def _sort_key(value: Any, /) -> tuple[int, str]:
    if value is None:
        return (0, "")
    if isinstance(value, datetime):
        return (1, value.isoformat())
    if isinstance(value, bool):
        return (1, str(int(value)))
    if isinstance(value, (int, float)):
        return (1, f"{value:030.10f}")
    return (1, str(value))


def _after(value: Any, cursor_value: Primitive, /) -> bool:
    return _sort_key(value) > _sort_key(cursor_value)
