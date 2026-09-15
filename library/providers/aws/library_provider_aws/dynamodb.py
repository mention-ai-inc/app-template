import copy
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Literal, Self, cast

from botocore.exceptions import ClientError

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
from library_provider_aws.clients import COLLECTION_INDEX_NAME, client, error_code, get_document_table_name
from library_provider_aws.queries import apply_field_updates, is_after_cursor, matches_every_filter, sort_documents
from library_provider_aws.serialization import AttributeValue, from_item, to_attribute_value, to_item
from library_provider_aws.transactions import (
    COLLECTION_ATTRIBUTE,
    DOCUMENT_ID_ATTRIBUTE,
    PARTITION_KEY_ATTRIBUTE,
    ROOT_SORT_KEY,
    SORT_KEY_ATTRIBUTE,
    SUBCOLLECTION_METADATA_ATTRIBUTE,
    VERSION_ATTRIBUTE,
    AwsTransaction,
    BufferedWrite,
    DocumentKey,
    partition_key,
    subdocument_sort_key,
)

BATCH_GET_LIMIT = 100
MUTATE_ATTEMPTS = 5
INTERNAL_ATTRIBUTES = frozenset(
    {
        PARTITION_KEY_ATTRIBUTE,
        SORT_KEY_ATTRIBUTE,
        COLLECTION_ATTRIBUTE,
        DOCUMENT_ID_ATTRIBUTE,
        VERSION_ATTRIBUTE,
        SUBCOLLECTION_METADATA_ATTRIBUTE,
    }
)
NoPartitionSelectedError = InfrastructureError(
    error_type=InfrastructureErrorType.QUERY_ERROR, message="Must select an Organization ID to use this collection"
)


class DynamoDbDocumentStore[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject]:
    @classmethod
    def to_document_id(cls, entity_id: str | int | ModelValueObject, /) -> DocumentID:
        if isinstance(entity_id, ModelValueObject):
            return DocumentID(entity_id.to_id())
        return DocumentID(str(entity_id))

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
        resolved_service = service if service is not None else os.getenv("SERVICE", "")
        self._service = resolved_service.value if isinstance(resolved_service, Service) else resolved_service
        self._feature_environment = feature_environment or os.getenv("FEATURE_ENVIRONMENT", "")
        self._collection_id = f"{self._feature_environment}{self._service}_{collection}"

    @contextmanager
    def connect_to_partition(self, partition_key_value: PartitionKeyT, /) -> Generator[Self]:
        scoped = copy.copy(self)
        scoped._collection_id = f"{self._feature_environment}{self._service}_{partition_key_value}_{self._collection}"
        scoped._active_partition_key = partition_key_value
        yield scoped

    @property
    def collection_id(self) -> str:
        return self._collection_id

    @property
    def active_partition_key(self) -> PartitionKeyT:
        if self._active_partition_key is None:
            raise NoPartitionSelectedError
        return self._active_partition_key

    async def get(self, *, document_id: DocumentID, uow: AwsTransaction | None = None) -> EntityT:
        self.__guard_read(uow)
        root, subdocuments = await self.__read_partition(document_id)
        self.__record_read(uow, document_id=document_id, root=root)

        if root is None:
            raise self.__not_found(document_id)

        return self._model.model_validate(self.__hydrate(root=root, subdocuments=subdocuments, deep=True))

    async def get_many(
        self, *, document_ids: list[DocumentID], uow: AwsTransaction | None = None, ignore_missing: bool = False
    ) -> list[EntityT]:
        self.__guard_read(uow)
        if len(document_ids) == 0:
            return []

        roots = await self.__batch_read_roots(document_ids)

        entities: list[EntityT] = []
        for document_id in document_ids:
            root = roots.get(document_id)
            self.__record_read(uow, document_id=document_id, root=root)

            if root is None:
                if ignore_missing:
                    continue
                raise self.__not_found(document_id)

            subdocuments = await self.__read_subdocuments(document_id) if self.__has_subentities() else {}
            entities.append(self._model.model_validate(self.__hydrate(root=root, subdocuments=subdocuments, deep=True)))

        return entities

    async def set(self, *, document_id: DocumentID, document_data: EntityT, uow: AwsTransaction | None = None) -> None:
        subentity_names = self._model.get_subentity_names()
        record = document_data.model_dump(exclude=set(subentity_names))
        committed = await self.__read_root(document_id)
        previous_metadata = (committed or {}).get(SUBCOLLECTION_METADATA_ATTRIBUTE, {})
        next_version = self.__version_of(committed) + 1

        metadata: dict[str, list[str]] = {}
        for subentity_name in subentity_names:
            metadata[subentity_name] = []
            subentities = cast(list[IEntity[Any]], getattr(document_data, subentity_name))
            for subentity in subentities:
                subdocument_id = self.to_document_id(subentity.id)
                sort_key = subdocument_sort_key(subentity_name=subentity_name, subdocument_id=subdocument_id)
                await self.__put(
                    uow,
                    key=(self.__partition_key(document_id), sort_key),
                    document={**subentity.model_dump(), VERSION_ATTRIBUTE: next_version},
                )
                metadata[subentity_name].append(subdocument_id)

            orphaned = set(cast(list[str], previous_metadata.get(subentity_name, []))) - set(metadata[subentity_name])
            for orphaned_subdocument_id in sorted(orphaned):
                sort_key = subdocument_sort_key(subentity_name=subentity_name, subdocument_id=orphaned_subdocument_id)
                await self.__delete_key(uow, key=(self.__partition_key(document_id), sort_key))

        await self.__put(
            uow,
            key=(self.__partition_key(document_id), ROOT_SORT_KEY),
            document={
                **record,
                COLLECTION_ATTRIBUTE: self._collection_id,
                DOCUMENT_ID_ATTRIBUTE: document_id,
                SUBCOLLECTION_METADATA_ATTRIBUTE: metadata,
                VERSION_ATTRIBUTE: next_version,
            },
        )

    async def update_fields(
        self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate], uow: AwsTransaction
    ) -> None:
        resolved = await self.__resolve_array_updates(document_id=document_id, field_updates=field_updates, uow=uow)
        expression, names, values = self.__update_expression(resolved)
        uow.buffer(
            BufferedWrite(
                key=(self.__partition_key(document_id), ROOT_SORT_KEY),
                operation="update",
                update_expression=expression,
                attribute_names=names,
                attribute_values=values,
            )
        )

    async def field_set(self, *, document_id: DocumentID, field: str, value: Primitive) -> None:
        await self.mutate_fields(document_id=document_id, field_updates={field: value})

    async def mutate_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate]) -> None:
        if not self.__needs_read_modify_write(field_updates):
            await self.__update_root(document_id=document_id, field_updates=field_updates, expected_version=None)
            return

        for _ in range(MUTATE_ATTEMPTS):
            committed = await self.__read_root(document_id)
            if committed is None:
                raise self.__not_found(document_id)

            resolved = self.__materialise_array_updates(document=committed, field_updates=field_updates)
            if await self.__update_root(
                document_id=document_id, field_updates=resolved, expected_version=self.__version_of(committed)
            ):
                return

        raise InfrastructureError(
            error_type=InfrastructureErrorType.CLOUD_ERROR,
            message=f"{self._collection_id}/{document_id} kept changing while its array fields were being mutated",
            public_message="Error connecting to the database. Probably temporary! Please try again.",
        )

    async def set_merge(self, *, document_id: DocumentID, document_data: dict[str, Any]) -> None:
        merged: dict[str, FieldUpdate] = {
            **cast(dict[str, FieldUpdate], document_data),
            COLLECTION_ATTRIBUTE: self._collection_id,
            DOCUMENT_ID_ATTRIBUTE: document_id,
        }
        await self.__update_root(document_id=document_id, field_updates=merged, expected_version=None, upsert=True)

    async def delete(self, *, document_id: DocumentID, uow: AwsTransaction | None = None) -> None:
        committed = await self.__read_root(document_id)
        metadata = cast(dict[str, list[str]], (committed or {}).get(SUBCOLLECTION_METADATA_ATTRIBUTE, {}))

        for subentity_name, subdocument_ids in metadata.items():
            for subdocument_id in subdocument_ids:
                sort_key = subdocument_sort_key(subentity_name=subentity_name, subdocument_id=subdocument_id)
                await self.__delete_key(uow, key=(self.__partition_key(document_id), sort_key))

        await self.__delete_key(uow, key=(self.__partition_key(document_id), ROOT_SORT_KEY))

    async def query(
        self,
        *,
        mode: Literal["shallow", "deep"] = "shallow",
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: AwsTransaction | None = None,
    ) -> QueryResult[EntityT]:
        self.__guard_read(uow)
        matched = await self.__matching_roots(filters=filters, cursor=cursor, sort_by=sort_by)
        subentity_names = self._model.get_subentity_names()

        entities: list[EntityT] = []
        subcollection_counts: list[dict[str, int]] = []
        for root in matched:
            document_id = DocumentID(str(root[DOCUMENT_ID_ATTRIBUTE]))
            self.__record_read(uow, document_id=document_id, root=root)
            metadata = cast(dict[str, list[str]], root.get(SUBCOLLECTION_METADATA_ATTRIBUTE, {}))
            subcollection_counts.append({name: len(metadata.get(name, [])) for name in subentity_names})
            subdocuments = (
                await self.__read_subdocuments(document_id) if mode == "deep" and self.__has_subentities() else {}
            )
            entities.append(
                self._model.model_validate(self.__hydrate(root=root, subdocuments=subdocuments, deep=mode == "deep"))
            )

        if limit is not None and len(entities) > limit:
            return QueryResult(
                entities=entities[:limit], subcollection_counts=subcollection_counts[:limit], has_more=True
            )

        return QueryResult(entities=entities, subcollection_counts=subcollection_counts, has_more=False)

    async def count(self, *, filters: list[QueryFilter] | None = None) -> int:
        return len(await self.__matching_roots(filters=filters, cursor=None, sort_by=None))

    async def query_ids(
        self,
        *,
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: AwsTransaction | None = None,
    ) -> list[DocumentID]:
        self.__guard_read(uow)
        matched = await self.__matching_roots(filters=filters, cursor=cursor, sort_by=sort_by)
        selected = matched if limit is None else matched[:limit]

        document_ids: list[DocumentID] = []
        for root in selected:
            document_id = DocumentID(str(root[DOCUMENT_ID_ATTRIBUTE]))
            self.__record_read(uow, document_id=document_id, root=root)
            document_ids.append(document_id)
        return document_ids

    async def query_one(self, *, filters: list[QueryFilter], uow: AwsTransaction | None = None) -> EntityT | None:
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
        return await self.__read_root(document_id) is not None

    def __partition_key(self, document_id: DocumentID, /) -> str:
        return partition_key(collection_id=self._collection_id, document_id=document_id)

    def __has_subentities(self) -> bool:
        return len(self._model.get_subentity_names()) > 0

    def __not_found(self, document_id: DocumentID, /) -> ApplicationError:
        return ApplicationError(
            error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
            message=f"{self._collection_id} entity with ID {document_id} not found",
            public_message="The requested resource was not found",
        )

    def __version_of(self, document: dict[str, Any] | None, /) -> int:
        if document is None:
            return 0
        version = document.get(VERSION_ATTRIBUTE, 0)
        return version if isinstance(version, int) else 0

    def __guard_read(self, uow: AwsTransaction | None, /) -> None:
        if uow is not None and uow.has_written:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=(
                    "Read after write inside a unit of work. Phase every read before the first write "
                    "(see .agents/rules/read-after-write.md)"
                ),
            )

    def __record_read(
        self, uow: AwsTransaction | None, /, *, document_id: DocumentID, root: dict[str, Any] | None
    ) -> None:
        if uow is None:
            return
        uow.record_read((self.__partition_key(document_id), ROOT_SORT_KEY), self.__version_of(root))

    def __hydrate(self, *, root: dict[str, Any], subdocuments: dict[str, dict[str, Any]], deep: bool) -> dict[str, Any]:
        hydrated = {name: value for name, value in root.items() if name not in INTERNAL_ATTRIBUTES}
        metadata = cast(dict[str, list[str]], root.get(SUBCOLLECTION_METADATA_ATTRIBUTE, {}))

        for subentity_name in self._model.get_subentity_names():
            if not deep:
                hydrated[subentity_name] = []
                continue
            hydrated[subentity_name] = [
                {name: value for name, value in subdocument.items() if name not in INTERNAL_ATTRIBUTES}
                for subdocument in (
                    subdocuments.get(subdocument_sort_key(subentity_name=subentity_name, subdocument_id=subdocument_id))
                    for subdocument_id in metadata.get(subentity_name, [])
                )
                if subdocument is not None
            ]

        return hydrated

    async def __read_partition(
        self, document_id: DocumentID, /
    ) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]]]:
        if not self.__has_subentities():
            return (await self.__read_root(document_id), {})

        items = await self.__query_partition(document_id)
        root = next((item for item in items if item[SORT_KEY_ATTRIBUTE] == ROOT_SORT_KEY), None)
        subdocuments = {
            str(item[SORT_KEY_ATTRIBUTE]): item for item in items if item[SORT_KEY_ATTRIBUTE] != ROOT_SORT_KEY
        }
        return (root, subdocuments)

    async def __read_subdocuments(self, document_id: DocumentID, /) -> dict[str, dict[str, Any]]:
        items = await self.__query_partition(document_id)
        return {str(item[SORT_KEY_ATTRIBUTE]): item for item in items if item[SORT_KEY_ATTRIBUTE] != ROOT_SORT_KEY}

    async def __query_partition(self, document_id: DocumentID, /) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        start_key: dict[str, AttributeValue] | None = None

        async with client("dynamodb") as dynamodb:
            while True:
                request: dict[str, Any] = {
                    "TableName": get_document_table_name(),
                    "KeyConditionExpression": "#partition_key_name = :partition_key_value",
                    "ExpressionAttributeNames": {"#partition_key_name": PARTITION_KEY_ATTRIBUTE},
                    "ExpressionAttributeValues": {
                        ":partition_key_value": to_attribute_value(self.__partition_key(document_id))
                    },
                }
                if start_key is not None:
                    request["ExclusiveStartKey"] = start_key
                response = await dynamodb.query(**request)
                items.extend(from_item(item) for item in response.get("Items", []))
                start_key = response.get("LastEvaluatedKey")
                if start_key is None:
                    return items

    async def __read_root(self, document_id: DocumentID, /) -> dict[str, Any] | None:
        async with client("dynamodb") as dynamodb:
            response = await dynamodb.get_item(
                TableName=get_document_table_name(),
                Key=self.__root_key_attributes(document_id),
                ConsistentRead=True,
            )
        item = response.get("Item")
        return None if item is None else from_item(item)

    async def __batch_read_roots(self, document_ids: list[DocumentID], /) -> dict[DocumentID, dict[str, Any]]:
        table_name = get_document_table_name()
        unique_ids = list(dict.fromkeys(document_ids))
        roots: dict[DocumentID, dict[str, Any]] = {}

        async with client("dynamodb") as dynamodb:
            for start in range(0, len(unique_ids), BATCH_GET_LIMIT):
                pending: list[dict[str, AttributeValue]] = [
                    self.__root_key_attributes(document_id)
                    for document_id in unique_ids[start : start + BATCH_GET_LIMIT]
                ]
                while len(pending) > 0:
                    response = await dynamodb.batch_get_item(
                        RequestItems={table_name: {"Keys": pending, "ConsistentRead": True}}
                    )
                    for item in response.get("Responses", {}).get(table_name, []):
                        document = from_item(item)
                        roots[DocumentID(str(document[DOCUMENT_ID_ATTRIBUTE]))] = document
                    pending = response.get("UnprocessedKeys", {}).get(table_name, {}).get("Keys", [])

        return roots

    async def __matching_roots(
        self, *, filters: list[QueryFilter] | None, cursor: dict[str, Primitive] | None, sort_by: SortBy | None
    ) -> list[dict[str, Any]]:
        roots = await self.__read_collection()
        matched = [root for root in roots if matches_every_filter(root, filters or [])]

        if sort_by is None:
            matched.sort(key=lambda root: str(root[DOCUMENT_ID_ATTRIBUTE]))
        else:
            matched = sort_documents(matched, sort_by)

        if cursor is not None:
            matched = [root for root in matched if is_after_cursor(root, cursor)]

        return matched

    async def __read_collection(self) -> list[dict[str, Any]]:
        roots: list[dict[str, Any]] = []
        start_key: dict[str, AttributeValue] | None = None

        async with client("dynamodb") as dynamodb:
            while True:
                request: dict[str, Any] = {
                    "TableName": get_document_table_name(),
                    "IndexName": COLLECTION_INDEX_NAME,
                    "KeyConditionExpression": "#collection_name = :collection_value",
                    "ExpressionAttributeNames": {"#collection_name": COLLECTION_ATTRIBUTE},
                    "ExpressionAttributeValues": {":collection_value": to_attribute_value(self._collection_id)},
                }
                if start_key is not None:
                    request["ExclusiveStartKey"] = start_key
                response = await dynamodb.query(**request)
                roots.extend(from_item(item) for item in response.get("Items", []))
                start_key = response.get("LastEvaluatedKey")
                if start_key is None:
                    return roots

    def __root_key_attributes(self, document_id: DocumentID, /) -> dict[str, AttributeValue]:
        return {
            PARTITION_KEY_ATTRIBUTE: to_attribute_value(self.__partition_key(document_id)),
            SORT_KEY_ATTRIBUTE: to_attribute_value(ROOT_SORT_KEY),
        }

    async def __put(self, uow: AwsTransaction | None, /, *, key: DocumentKey, document: dict[str, Any]) -> None:
        item = to_item({**document, PARTITION_KEY_ATTRIBUTE: key[0], SORT_KEY_ATTRIBUTE: key[1]})
        if uow is not None:
            uow.buffer(BufferedWrite(key=key, operation="put", item=item))
            return

        async with client("dynamodb") as dynamodb:
            await dynamodb.put_item(TableName=get_document_table_name(), Item=item)

    async def __delete_key(self, uow: AwsTransaction | None, /, *, key: DocumentKey) -> None:
        if uow is not None:
            uow.buffer(BufferedWrite(key=key, operation="delete"))
            return

        async with client("dynamodb") as dynamodb:
            await dynamodb.delete_item(
                TableName=get_document_table_name(),
                Key={
                    PARTITION_KEY_ATTRIBUTE: to_attribute_value(key[0]),
                    SORT_KEY_ATTRIBUTE: to_attribute_value(key[1]),
                },
            )

    def __needs_read_modify_write(self, field_updates: dict[str, FieldUpdate], /) -> bool:
        return any(isinstance(update, (ArrayUnion, ArrayRemove)) for update in field_updates.values())

    def __materialise_array_updates(
        self, *, document: dict[str, Any], field_updates: dict[str, FieldUpdate]
    ) -> dict[str, FieldUpdate]:
        array_updates: dict[str, FieldUpdate] = {
            name: update for name, update in field_updates.items() if isinstance(update, (ArrayUnion, ArrayRemove))
        }
        materialised = apply_field_updates(document, array_updates)
        return {
            name: cast(FieldUpdate, materialised[name]) if name in array_updates else update
            for name, update in field_updates.items()
        }

    async def __resolve_array_updates(
        self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate], uow: AwsTransaction
    ) -> dict[str, FieldUpdate]:
        if not self.__needs_read_modify_write(field_updates):
            return field_updates

        committed = await self.__read_root(document_id)
        uow.record_read((self.__partition_key(document_id), ROOT_SORT_KEY), self.__version_of(committed))
        return self.__materialise_array_updates(document=committed or {}, field_updates=field_updates)

    def __update_expression(
        self, field_updates: dict[str, FieldUpdate], /
    ) -> tuple[str, dict[str, str], dict[str, AttributeValue]]:
        names: dict[str, str] = {"#version_name": VERSION_ATTRIBUTE}
        values: dict[str, AttributeValue] = {":version_step": to_attribute_value(1)}
        set_clauses: list[str] = []
        add_clauses: list[str] = ["#version_name :version_step"]

        for position, (name, update) in enumerate(field_updates.items()):
            placeholder_name = f"#field_{position}"
            placeholder_value = f":value_{position}"
            names[placeholder_name] = name
            if isinstance(update, Increment):
                values[placeholder_value] = to_attribute_value(update.value)
                add_clauses.append(f"{placeholder_name} {placeholder_value}")
            else:
                values[placeholder_value] = to_attribute_value(update)
                set_clauses.append(f"{placeholder_name} = {placeholder_value}")

        expression = f"ADD {', '.join(add_clauses)}"
        if len(set_clauses) > 0:
            expression = f"SET {', '.join(set_clauses)} {expression}"
        return (expression, names, values)

    async def __update_root(
        self,
        *,
        document_id: DocumentID,
        field_updates: dict[str, FieldUpdate],
        expected_version: int | None,
        upsert: bool = False,
    ) -> bool:
        expression, names, values = self.__update_expression(field_updates)
        request: dict[str, Any] = {
            "TableName": get_document_table_name(),
            "Key": self.__root_key_attributes(document_id),
            "UpdateExpression": expression,
            "ExpressionAttributeNames": names,
            "ExpressionAttributeValues": values,
        }

        if expected_version is not None:
            request["ExpressionAttributeNames"] = {**names, "#expected_version_name": VERSION_ATTRIBUTE}
            request["ExpressionAttributeValues"] = {
                **values,
                ":expected_version": to_attribute_value(expected_version),
            }
            request["ConditionExpression"] = "#expected_version_name = :expected_version"
        elif not upsert:
            request["ConditionExpression"] = f"attribute_exists({PARTITION_KEY_ATTRIBUTE})"

        try:
            async with client("dynamodb") as dynamodb:
                await dynamodb.update_item(**request)
        except ClientError as error:
            if error_code(error) != "ConditionalCheckFailedException":
                raise
            if expected_version is not None:
                return False
            raise self.__not_found(document_id) from error

        return True
