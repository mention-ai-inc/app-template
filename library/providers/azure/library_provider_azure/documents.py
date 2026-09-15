import copy
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Literal, Self, cast

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.documents import (
    ArrayRemove,
    ArrayUnion,
    DocumentID,
    FieldUpdate,
    Increment,
    Primitive,
    QueryFilter,
    QueryResult,
    SortBy,
)
from library.domain.entities import IEntity
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import feature_environment
from library_provider_azure.transactions import BufferedWrite, CosmosTransaction

DOCUMENT_TYPE_FIELD = "documentType"
DOCUMENT_ID_FIELD = "documentId"
ENTITY_ID_FIELD = "entityId"
PARTITION_KEY_FIELD = "partitionKey"
ORGANIZATION_FIELD = "organization_id"
ETAG_FIELD = "_etag"
SUBCOLLECTION_METADATA_FIELD = "_subcollection_metadata"
SUBCOLLECTION_SEPARATOR = "|"
COSMOS_SYSTEM_FIELDS = frozenset({"_rid", "_self", ETAG_FIELD, "_attachments", "_ts"})
RESERVED_FIELDS = COSMOS_SYSTEM_FIELDS | {
    "id",
    DOCUMENT_TYPE_FIELD,
    DOCUMENT_ID_FIELD,
    ENTITY_ID_FIELD,
    PARTITION_KEY_FIELD,
}
ILLEGAL_ID_CHARACTERS = ("/", "\\", "?", "#")
SQL_COMPARISONS = {"==": "=", "!=": "!=", ">": ">", ">=": ">=", "<": "<", "<=": "<="}
COMPUTED_UPDATES = (Increment, ArrayUnion, ArrayRemove)

NoPartitionSelectedError = InfrastructureError(
    error_type=InfrastructureErrorType.QUERY_ERROR, message="Must select an Organization ID to use this collection"
)


def to_cosmos_value(value: Any, /) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [to_cosmos_value(member) for member in cast(list[Any], value)]
    return value


def to_cosmos_id(*, document_type: str, document_id: DocumentID) -> str:
    cosmos_id = f"{document_type}:{document_id}"
    for character in ILLEGAL_ID_CHARACTERS:
        if character in cosmos_id:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.VALIDATION_ERROR,
                message=f"A Cosmos DB item id cannot contain {character!r}: {cosmos_id}",
            )
    return cosmos_id


def to_subcollection_type(*, collection_id: str, document_id: DocumentID, subentity_name: str) -> str:
    return SUBCOLLECTION_SEPARATOR.join([collection_id, document_id, subentity_name])


def to_partition_value(*, collection_id: str, record: dict[str, Any]) -> str:
    organization_id = record.get(ORGANIZATION_FIELD)
    if isinstance(organization_id, str) and organization_id:
        return organization_id
    return collection_id


def to_cosmos_item(
    *, document_type: str, document_id: DocumentID, partition_value: str, record: dict[str, Any]
) -> dict[str, Any]:
    body = {field: value for field, value in record.items() if field not in RESERVED_FIELDS}
    return {
        **body,
        "id": to_cosmos_id(document_type=document_type, document_id=document_id),
        DOCUMENT_TYPE_FIELD: document_type,
        DOCUMENT_ID_FIELD: document_id,
        ENTITY_ID_FIELD: record.get("id", document_id),
        PARTITION_KEY_FIELD: partition_value,
    }


def to_record(item: dict[str, Any], /) -> dict[str, Any]:
    record = {field: value for field, value in item.items() if field not in RESERVED_FIELDS}
    record["id"] = item[ENTITY_ID_FIELD]
    return record


def to_patch_operations(field_updates: dict[str, FieldUpdate], /, *, item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"op": "set", "path": f"/{field}", "value": to_patched_value(update, item=item, field=field)}
        for field, update in field_updates.items()
    ]


def to_patched_value(update: FieldUpdate, /, *, item: dict[str, Any], field: str) -> Any:
    if isinstance(update, Increment):
        current = item.get(field)
        base = current if isinstance(current, (int, float)) and not isinstance(current, bool) else 0
        return base + update.value
    if isinstance(update, ArrayUnion):
        existing = list(cast(list[Any], item.get(field, [])))
        return to_cosmos_value(existing + [value for value in update.values if value not in existing])
    if isinstance(update, ArrayRemove):
        existing = list(cast(list[Any], item.get(field, [])))
        return to_cosmos_value([value for value in existing if value not in update.values])
    return to_cosmos_value(update)


def to_sql_condition(*, field: str, operator: str, name: str) -> str:
    if operator == "in":
        return f"ARRAY_CONTAINS({name}, c.{field})"
    if operator == "not_in":
        return f"NOT ARRAY_CONTAINS({name}, c.{field})"
    if operator == "array_contains":
        return f"ARRAY_CONTAINS(c.{field}, {name})"

    comparison = SQL_COMPARISONS.get(operator)
    if comparison is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.QUERY_ERROR,
            message=f"Cosmos DB has no SQL comparison for the query operator {operator!r}",
        )
    return f"c.{field} {comparison} {name}"


class CosmosDocumentStore[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject]:
    def __init__(
        self,
        *,
        collection: str,
        model: type[EntityT],
        partition_key_type: type[PartitionKeyT],
        service: Service | str | None = None,
        feature_environment_override: str | None = None,
    ) -> None:
        self._collection = collection
        self._model = model
        self._partition_key_type = partition_key_type
        self._active_partition_key: PartitionKeyT | None = None
        resolved_service = service if service is not None else os.getenv("SERVICE", "")
        self._service = resolved_service.value if isinstance(resolved_service, Service) else resolved_service
        self._feature_environment = feature_environment_override or feature_environment()
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

    @property
    def container_name(self) -> str:
        if not self._service:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message="Cosmos DB holds one container per service, so a document store needs a service",
            )
        return self._service

    async def get(self, *, document_id: DocumentID, uow: CosmosTransaction | None = None) -> EntityT:
        self.__guard_read(uow)
        item = await self.__read(document_id=document_id)
        self.__record_read(uow, document_id=document_id, item=item)

        if item is None:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"{self._collection_id} entity with ID {document_id} not found",
                public_message="The requested resource was not found",
            )

        return self._model.model_validate(await self.__hydrate(item=item, deep=True))

    async def get_many(
        self, *, document_ids: list[DocumentID], uow: CosmosTransaction | None = None, ignore_missing: bool = False
    ) -> list[EntityT]:
        entities: list[EntityT] = []
        for document_id in document_ids:
            if ignore_missing and await self.__read(document_id=document_id) is None:
                continue
            entities.append(await self.get(document_id=document_id, uow=uow))
        return entities

    async def set(
        self, *, document_id: DocumentID, document_data: EntityT, uow: CosmosTransaction | None = None
    ) -> None:
        subentity_names = self._model.get_subentity_names()
        record = document_data.model_dump(mode="json", exclude=set(subentity_names))
        partition_value = self.__resolved_partition_value(record=record)
        previous_metadata = await self.__committed_subcollection_metadata(
            document_id=document_id, subentity_names=subentity_names
        )

        metadata: dict[str, list[str]] = {}
        for subentity_name in subentity_names:
            metadata[subentity_name] = []
            subcollection_type = to_subcollection_type(
                collection_id=self._collection_id, document_id=document_id, subentity_name=subentity_name
            )
            subentities = cast(list[IEntity[Any]], getattr(document_data, subentity_name))
            for subentity in subentities:
                subdocument_id = self.to_document_id(subentity.id)
                await self.__write(
                    uow,
                    item=to_cosmos_item(
                        document_type=subcollection_type,
                        document_id=subdocument_id,
                        partition_value=partition_value,
                        record=subentity.model_dump(mode="json"),
                    ),
                    partition_value=partition_value,
                )
                metadata[subentity_name].append(subdocument_id)

            orphaned = set(previous_metadata.get(subentity_name, [])) - set(metadata[subentity_name])
            for orphaned_subdocument_id in sorted(orphaned):
                await self.__remove(
                    uow,
                    cosmos_id=to_cosmos_id(
                        document_type=subcollection_type, document_id=DocumentID(orphaned_subdocument_id)
                    ),
                    partition_value=partition_value,
                )

        await self.__write(
            uow,
            item=to_cosmos_item(
                document_type=self._collection_id,
                document_id=document_id,
                partition_value=partition_value,
                record={**record, SUBCOLLECTION_METADATA_FIELD: metadata},
            ),
            partition_value=partition_value,
        )

    async def update_fields(
        self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate], uow: CosmosTransaction
    ) -> None:
        cosmos_id = to_cosmos_id(document_type=self._collection_id, document_id=document_id)
        item = None if self.__updates_are_self_contained(field_updates) else await self.__read(document_id=document_id)

        if item is None and self._active_partition_key is None:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"{self._collection_id} entity with ID {document_id} not found",
                public_message="The requested resource was not found",
            )

        uow.has_written = True
        uow.writes.append(
            BufferedWrite(
                container_name=self.container_name,
                cosmos_id=cosmos_id,
                partition_value=item[PARTITION_KEY_FIELD] if item is not None else self.active_partition_key,
                operation="patch",
                item=None,
                patch_operations=to_patch_operations(field_updates, item=item or {}),
                etag=uow.read_etags.get((self.container_name, cosmos_id)),
            )
        )

    async def field_set(self, *, document_id: DocumentID, field: str, value: Primitive) -> None:
        await self.mutate_fields(document_id=document_id, field_updates={field: value})

    async def mutate_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate]) -> None:
        item = await self.__read(document_id=document_id)
        if item is None:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"{self._collection_id} entity with ID {document_id} not found",
                public_message="The requested resource was not found",
            )

        await self.__container().patch_item(
            item=item["id"],
            partition_key=item[PARTITION_KEY_FIELD],
            patch_operations=to_patch_operations(field_updates, item=item),
        )

    async def set_merge(self, *, document_id: DocumentID, document_data: dict[str, Any]) -> None:
        item = await self.__read(document_id=document_id)
        record = {} if item is None else {field: value for field, value in item.items() if field not in RESERVED_FIELDS}
        merged = {**record, **{field: to_cosmos_value(value) for field, value in document_data.items()}}
        partition_value = (
            item[PARTITION_KEY_FIELD] if item is not None else self.__resolved_partition_value(record=merged)
        )

        await self.__container().upsert_item(
            body=to_cosmos_item(
                document_type=self._collection_id,
                document_id=document_id,
                partition_value=partition_value,
                record={**merged, "id": item[ENTITY_ID_FIELD] if item is not None else document_id},
            )
        )

    async def delete(self, *, document_id: DocumentID, uow: CosmosTransaction | None = None) -> None:
        item = await self.__read(document_id=document_id)
        if item is None:
            return

        partition_value: str = item[PARTITION_KEY_FIELD]
        metadata: dict[str, list[str]] = item.get(SUBCOLLECTION_METADATA_FIELD, {})
        for subentity_name, subdocument_ids in metadata.items():
            subcollection_type = to_subcollection_type(
                collection_id=self._collection_id, document_id=document_id, subentity_name=subentity_name
            )
            for subdocument_id in subdocument_ids:
                await self.__remove(
                    uow,
                    cosmos_id=to_cosmos_id(document_type=subcollection_type, document_id=DocumentID(subdocument_id)),
                    partition_value=partition_value,
                )

        await self.__remove(uow, cosmos_id=item["id"], partition_value=partition_value)

    async def query(
        self,
        *,
        mode: Literal["shallow", "deep"] = "shallow",
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: CosmosTransaction | None = None,
    ) -> QueryResult[EntityT]:
        self.__guard_read(uow)
        items = await self.__run_query(
            projection="*", filters=filters, cursor=cursor, limit=None if limit is None else limit + 1, sort_by=sort_by
        )
        subentity_names = self._model.get_subentity_names()

        entities: list[EntityT] = []
        subcollection_counts: list[dict[str, int]] = []
        for item in items:
            self.__record_read(uow, document_id=DocumentID(item[DOCUMENT_ID_FIELD]), item=item)
            metadata: dict[str, list[str]] = item.get(SUBCOLLECTION_METADATA_FIELD, {})
            subcollection_counts.append({name: len(metadata.get(name, [])) for name in subentity_names})
            entities.append(self._model.model_validate(await self.__hydrate(item=item, deep=mode == "deep")))

        if limit is not None and len(entities) > limit:
            return QueryResult(
                entities=entities[:limit], subcollection_counts=subcollection_counts[:limit], has_more=True
            )

        return QueryResult(entities=entities, subcollection_counts=subcollection_counts, has_more=False)

    async def count(self, *, filters: list[QueryFilter] | None = None) -> int:
        where, parameters = self.__where(filters=filters, cursor=None, sort_by=None)
        counts = [
            cast(int, count)
            async for count in self.__container().query_items(
                query=f"SELECT VALUE COUNT(1) FROM c{where}", parameters=parameters
            )
        ]
        return counts[0] if counts else 0

    async def query_ids(
        self,
        *,
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: CosmosTransaction | None = None,
    ) -> list[DocumentID]:
        self.__guard_read(uow)
        items = await self.__run_query(
            projection=f"c.{DOCUMENT_ID_FIELD}", filters=filters, cursor=cursor, limit=limit, sort_by=sort_by
        )
        return [DocumentID(item[DOCUMENT_ID_FIELD]) for item in items]

    async def query_one(self, *, filters: list[QueryFilter], uow: CosmosTransaction | None = None) -> EntityT | None:
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
        return await self.__read(document_id=document_id) is not None

    def __container(self) -> ContainerProxy:
        return AzureClients.container(self.container_name)

    def __resolved_partition_value(self, *, record: dict[str, Any]) -> str:
        if self._active_partition_key is not None:
            return self._active_partition_key
        return to_partition_value(collection_id=self._collection_id, record=record)

    def __updates_are_self_contained(self, field_updates: dict[str, FieldUpdate], /) -> bool:
        if self._active_partition_key is None:
            return False
        return not any(isinstance(update, COMPUTED_UPDATES) for update in field_updates.values())

    async def __read(self, *, document_id: DocumentID) -> dict[str, Any] | None:
        cosmos_id = to_cosmos_id(document_type=self._collection_id, document_id=document_id)

        if self._active_partition_key is not None:
            return await self.__read_in_partition(cosmos_id=cosmos_id, partition_value=self._active_partition_key)

        items = [
            item
            async for item in self.__container().query_items(
                query="SELECT * FROM c WHERE c.id = @id", parameters=[{"name": "@id", "value": cosmos_id}]
            )
        ]
        return items[0] if items else None

    async def __read_in_partition(self, *, cosmos_id: str, partition_value: str) -> dict[str, Any] | None:
        try:
            return await self.__container().read_item(item=cosmos_id, partition_key=partition_value)
        except CosmosResourceNotFoundError:
            return None

    async def __hydrate(self, *, item: dict[str, Any], deep: bool) -> dict[str, Any]:
        record = to_record(item)
        document_id = DocumentID(item[DOCUMENT_ID_FIELD])
        metadata: dict[str, list[str]] = record.get(SUBCOLLECTION_METADATA_FIELD, {})

        for subentity_name in self._model.get_subentity_names():
            if not deep:
                record[subentity_name] = []
                continue
            subcollection_type = to_subcollection_type(
                collection_id=self._collection_id, document_id=document_id, subentity_name=subentity_name
            )
            subrecords: list[dict[str, Any]] = []
            for subdocument_id in metadata.get(subentity_name, []):
                subitem = await self.__read_in_partition(
                    cosmos_id=to_cosmos_id(document_type=subcollection_type, document_id=DocumentID(subdocument_id)),
                    partition_value=item[PARTITION_KEY_FIELD],
                )
                if subitem is not None:
                    subrecords.append(to_record(subitem))
            record[subentity_name] = subrecords

        return record

    async def __committed_subcollection_metadata(
        self, *, document_id: DocumentID, subentity_names: list[str]
    ) -> dict[str, list[str]]:
        if len(subentity_names) == 0:
            return {}

        item = await self.__read(document_id=document_id)
        if item is None:
            return {}

        return item.get(SUBCOLLECTION_METADATA_FIELD, {})

    def __where(
        self, *, filters: list[QueryFilter] | None, cursor: dict[str, Primitive] | None, sort_by: SortBy | None
    ) -> tuple[str, list[dict[str, Any]]]:
        conditions = [f"c.{DOCUMENT_TYPE_FIELD} = @documentType"]
        parameters: list[dict[str, Any]] = [{"name": "@documentType", "value": self._collection_id}]

        for index, query_filter in enumerate(filters or []):
            name = f"@filter{index}"
            parameters.append({"name": name, "value": to_cosmos_value(query_filter.value)})
            conditions.append(to_sql_condition(field=query_filter.field, operator=query_filter.operator, name=name))

        comparison = "<" if sort_by is not None and sort_by.direction == "DESCENDING" else ">"
        for index, (field, value) in enumerate((cursor or {}).items()):
            name = f"@cursor{index}"
            parameters.append({"name": name, "value": to_cosmos_value(value)})
            conditions.append(f"c.{field} {comparison} {name}")

        return f" WHERE {' AND '.join(conditions)}", parameters

    async def __run_query(
        self,
        *,
        projection: str,
        filters: list[QueryFilter] | None,
        cursor: dict[str, Primitive] | None,
        limit: int | None,
        sort_by: SortBy | None,
    ) -> list[dict[str, Any]]:
        where, parameters = self.__where(filters=filters, cursor=cursor, sort_by=sort_by)
        order_by = ""
        if sort_by is not None:
            order_by = f" ORDER BY c.{sort_by.field} {'DESC' if sort_by.direction == 'DESCENDING' else 'ASC'}"
        elif cursor:
            order_by = " ORDER BY " + ", ".join(f"c.{field} ASC" for field in cursor)

        page = "" if limit is None else f" OFFSET 0 LIMIT {limit}"
        query = f"SELECT {projection} FROM c{where}{order_by}{page}"

        return [item async for item in self.__container().query_items(query=query, parameters=parameters)]

    async def __write(self, uow: CosmosTransaction | None, *, item: dict[str, Any], partition_value: str) -> None:
        if uow is None:
            await self.__container().upsert_item(body=item)
            return

        uow.has_written = True
        uow.writes.append(
            BufferedWrite(
                container_name=self.container_name,
                cosmos_id=item["id"],
                partition_value=partition_value,
                operation="upsert",
                item=item,
                patch_operations=None,
                etag=uow.read_etags.get((self.container_name, item["id"])),
            )
        )

    async def __remove(self, uow: CosmosTransaction | None, *, cosmos_id: str, partition_value: str) -> None:
        if uow is None:
            try:
                await self.__container().delete_item(item=cosmos_id, partition_key=partition_value)
            except CosmosResourceNotFoundError:
                return
            return

        uow.has_written = True
        uow.writes.append(
            BufferedWrite(
                container_name=self.container_name,
                cosmos_id=cosmos_id,
                partition_value=partition_value,
                operation="delete",
                item=None,
                patch_operations=None,
                etag=uow.read_etags.get((self.container_name, cosmos_id)),
            )
        )

    def __record_read(
        self, uow: CosmosTransaction | None, *, document_id: DocumentID, item: dict[str, Any] | None
    ) -> None:
        if uow is None:
            return
        cosmos_id = to_cosmos_id(document_type=self._collection_id, document_id=document_id)
        uow.read_etags[(self.container_name, cosmos_id)] = None if item is None else item.get(ETAG_FIELD)

    def __guard_read(self, uow: CosmosTransaction | None) -> None:
        if uow is not None and uow.has_written:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=(
                    "Read after write inside a unit of work. Phase every read before the first write "
                    "(see .agents/rules/read-after-write.md)"
                ),
            )
