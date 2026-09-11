import copy
import os
import re
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, NewType, Protocol, Self, cast

from google.cloud import firestore
from google.cloud.firestore import ArrayRemove, ArrayUnion, FieldFilter, Increment
from google.cloud.firestore_admin_v1 import FirestoreAdminClient
from google.cloud.firestore_v1 import DocumentSnapshot
from google.cloud.firestore_v1.types import DocumentChange
from pydantic import BaseModel, model_validator

from library.application.errors import ApplicationError, ApplicationErrorType
from library.domain.entities import IEntity
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject, ModelValueObject, StringValueObject
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType

UOW = NewType("UOW", firestore.AsyncTransaction)
DocumentID = NewType("DocumentID", str)
Primitive = (
    bool | str | int | float | datetime | Sequence[str] | Sequence[int] | Sequence[float] | Sequence[datetime] | None
)
FieldUpdate = Primitive | Increment | ArrayUnion | ArrayRemove
NoOrganizationIDSelectedError = InfrastructureError(
    error_type=InfrastructureErrorType.QUERY_ERROR, message="Must select an Organization ID to use this collection"
)


class IOnSnapshot(Protocol):
    def __call__(
        self, doc_snapshot: list[DocumentSnapshot], changes: list[DocumentChange], read_time: datetime
    ) -> None: ...


class QueryFilter(BaseModel):
    field: str
    operator: Literal["==", "!=", ">", ">=", "<", "<=", "array_contains", "in", "not_in"]
    value: Primitive

    @model_validator(mode="after")
    def in_cannot_be_longer_than_30_items(self) -> Self:
        if self.operator == "in" and isinstance(self.value, list) and (len(self.value) > 30):
            raise InfrastructureError(
                error_type=InfrastructureErrorType.VALIDATION_ERROR,
                message="Database 'in' cannot be longer than 30 items",
            )
        return self


class SortBy(BaseModel):
    field: str
    direction: Literal["ASCENDING", "DESCENDING"]


@dataclass
class QueryResult[EntityT: IEntity[Any]]:
    entities: list[EntityT]
    subcollection_counts: list[dict[str, int]]
    has_more: bool


class Firestore[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject]:
    IN_QUERY_MAX_ITEMS = 30
    DATABASE_NAME = "(default)"
    DEFAULT_CLIENT_POOL_SIZE = 8
    _client_pool: list[firestore.AsyncClient] | None = None
    _client_pool_cursor: int = 0
    _sync_client: firestore.Client | None = None
    _admin_client: FirestoreAdminClient | None = None
    _vector_fields: dict[str, list[str]] | None = None

    @classmethod
    def get_client(cls) -> firestore.AsyncClient:
        if cls._client_pool is None:
            cls._client_pool = [firestore.AsyncClient() for _ in range(cls.DEFAULT_CLIENT_POOL_SIZE)]
        client = cls._client_pool[cls._client_pool_cursor]
        cls._client_pool_cursor = (cls._client_pool_cursor + 1) % len(cls._client_pool)
        return client

    @classmethod
    def client_for_uow(cls, uow: UOW | None) -> firestore.AsyncClient:
        if uow is not None:
            return uow._client  # pyright: ignore[reportPrivateUsage]
        return cls.get_client()

    @classmethod
    def get_sync_client(cls) -> firestore.Client:
        if cls._sync_client is None:
            cls._sync_client = firestore.Client()
        return cls._sync_client

    @classmethod
    def get_admin_client(cls) -> FirestoreAdminClient:
        if cls._admin_client is None:
            cls._admin_client = FirestoreAdminClient()
        return cls._admin_client

    @classmethod
    def get_partition_keys_with_data(cls, *, partition_key_type: type[PartitionKeyT]) -> list[PartitionKeyT]:
        collections = cls.get_sync_client().collections()
        partition_key_matches = [re.search("((user)_[a-zA-Z0-9]+)", collection.id) for collection in collections]
        return [partition_key_type(match.group(1)) for match in partition_key_matches if match is not None]

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
            raise NoOrganizationIDSelectedError
        return self._active_partition_key

    async def get(self, *, document_id: DocumentID, uow: UOW | None = None) -> EntityT:
        raw_entity_ref = self.client_for_uow(uow).collection(self._collection_id).document(document_id)
        raw_entity_snapshot = await raw_entity_ref.get(transaction=uow)

        if not raw_entity_snapshot.exists:
            raise ApplicationError(
                error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                message=f"{self._collection_id} entity with ID {document_id} not found",
                public_message="The requested resource was not found",
            )

        root_entity = raw_entity_snapshot.to_dict() or {}

        for subentity_name in self._model.get_subentity_names():
            collection = raw_entity_ref.collection(subentity_name)
            entity_ids = root_entity.get("_subcollection_metadata", {}).get(subentity_name, [])
            root_entity[subentity_name] = [
                (await collection.document(entity_id).get(transaction=uow)).to_dict() for entity_id in entity_ids
            ]

        return self._model.model_validate(root_entity)

    async def get_many(
        self, *, document_ids: list[DocumentID], uow: UOW | None = None, ignore_missing: bool = False
    ) -> list[EntityT]:
        if len(document_ids) == 0:
            return []

        client = self.client_for_uow(uow)
        doc_refs = [client.collection(self._collection_id).document(document_id) for document_id in document_ids]

        raw_entity_snapshots = [snapshot async for snapshot in client.get_all(doc_refs, transaction=uow)]

        parsed_entities: list[EntityT] = []
        for raw_entity_snapshot in raw_entity_snapshots:
            if not raw_entity_snapshot.exists:
                if ignore_missing:
                    continue
                raise ApplicationError(
                    error_type=ApplicationErrorType.RESOURCE_NOT_FOUND,
                    message=f"{self._collection_id} entity with ID {raw_entity_snapshot.id} not found",
                    public_message="The requested resource was not found",
                )

            root_entity = raw_entity_snapshot.to_dict() or {}

            for subentity_name in self._model.get_subentity_names():
                collection = raw_entity_snapshot.reference.collection(subentity_name)
                entity_ids = root_entity.get("_subcollection_metadata", {}).get(subentity_name, [])
                root_entity[subentity_name] = [
                    (await collection.document(entity_id).get(transaction=uow)).to_dict() for entity_id in entity_ids
                ]

            parsed_entities.append(self._model.model_validate(root_entity))

        return parsed_entities

    async def set(self, *, document_id: DocumentID, document_data: EntityT, uow: UOW | None = None) -> None:
        document = self.client_for_uow(uow).collection(self._collection_id).document(document_id)
        subentity_names = self._model.get_subentity_names()
        dumped_document_data = document_data.model_dump(exclude=set(subentity_names))

        previous_subcollection_metadata = await self.__read_committed_subcollection_metadata(
            document_id=document_id, subentity_names=subentity_names
        )

        subcollection_metadata: dict[str, list[str]] = {}
        for subentity_name in subentity_names:
            subcollection_metadata[subentity_name] = []
            subentity_collection = document.collection(subentity_name)
            subentities = cast(list[IEntity[Any]], getattr(document_data, subentity_name))
            for subentity in subentities:
                subdocument_id = self.to_document_id(subentity.id)
                record_document = subentity_collection.document(subdocument_id)
                if uow is None:
                    await record_document.set(subentity.model_dump())
                else:
                    uow.set(cast(firestore.DocumentReference, record_document), subentity.model_dump())
                subcollection_metadata[subentity_name].append(subdocument_id)

            orphaned_subdocument_ids = set(previous_subcollection_metadata.get(subentity_name, [])) - set(
                subcollection_metadata[subentity_name]
            )
            for orphaned_subdocument_id in sorted(orphaned_subdocument_ids):
                orphaned_document = subentity_collection.document(orphaned_subdocument_id)
                if uow is None:
                    await orphaned_document.delete()
                else:
                    uow.delete(cast(firestore.DocumentReference, orphaned_document))

        record = {**dumped_document_data, "_subcollection_metadata": subcollection_metadata}
        if uow is None:
            await document.set(record)
        else:
            uow.set(document, record)

    async def update_fields(
        self,
        *,
        document_id: DocumentID,
        field_updates: dict[str, FieldUpdate],
        uow: UOW,
    ) -> None:
        document = self.client_for_uow(uow).collection(self._collection_id).document(document_id)
        uow.update(document, field_updates)

    async def field_set(self, *, document_id: DocumentID, field: str, value: Primitive) -> None:
        document = self.get_client().collection(self._collection_id).document(document_id)
        await document.update({field: value})  # does not use transaction

    async def mutate_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate]) -> None:
        document = self.get_client().collection(self._collection_id).document(document_id)
        await document.update(field_updates)  # does not use transaction

    async def set_merge(self, *, document_id: DocumentID, document_data: dict[str, Any]) -> None:
        document = self.get_client().collection(self._collection_id).document(document_id)
        await document.set(document_data, merge=True)  # does not use transaction

    async def delete(self, *, document_id: DocumentID, uow: UOW | None = None) -> None:
        document = self.client_for_uow(uow).collection(self._collection_id).document(document_id)
        subentity_names = self._model.get_subentity_names()

        if len(subentity_names) > 0:
            existing_doc = await document.get()
            if existing_doc.exists:
                existing_data = existing_doc.to_dict() or {}
                subcollection_metadata: dict[str, list[str]] = existing_data.get("_subcollection_metadata", {})

                for subcollection_key, doc_ids in subcollection_metadata.items():
                    subcollection = document.collection(subcollection_key)
                    for doc_id in doc_ids:
                        record_document = subcollection.document(doc_id)
                        if uow is None:
                            await record_document.delete()
                        else:
                            uow.delete(cast(firestore.DocumentReference, record_document))

        if uow is None:
            await document.delete()
        else:
            uow.delete(document)

    async def query(
        self,
        *,
        mode: Literal["shallow", "deep"] = "shallow",
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: UOW | None = None,
    ) -> QueryResult[EntityT]:
        base_query = self.client_for_uow(uow).collection(self._collection_id)

        for filter_ in filters or []:
            base_query = base_query.where(filter=FieldFilter(filter_.field, filter_.operator, filter_.value))

        if cursor is not None:
            for field in cursor:
                base_query = base_query.order_by(field)
            base_query = base_query.start_after(cursor)

        if limit is not None:
            base_query = base_query.limit(limit + 1)  # +1 to check if there are more results

        if sort_by is not None:
            base_query = base_query.order_by(sort_by.field, direction=sort_by.direction)

        raw_entities = await base_query.get(transaction=uow)  # type: ignore
        subentity_names = self._model.get_subentity_names()

        reads: list[EntityT] = []
        subcollection_counts: list[dict[str, int]] = []

        for raw_entity in raw_entities:
            root_entity = raw_entity.to_dict() or {}
            entity_subcollection_counts = {
                name: len(root_entity.get("_subcollection_metadata", {}).get(name, [])) for name in subentity_names
            }
            subcollection_counts.append(entity_subcollection_counts)
            if mode == "deep":
                for subentity_name in subentity_names:
                    collection = raw_entity.reference.collection(subentity_name)
                    entity_ids = root_entity.get("_subcollection_metadata", {}).get(subentity_name, [])
                    root_entity[subentity_name] = [
                        (await collection.document(entity_id).get()).to_dict() for entity_id in entity_ids
                    ]
            else:
                for subentity_name in subentity_names:
                    root_entity[subentity_name] = []

            reads.append(self._model.model_validate(root_entity))

        if limit is not None and len(reads) > limit:
            has_more = True
            reads = reads[:limit]
        else:
            has_more = False

        return QueryResult(entities=reads, subcollection_counts=subcollection_counts, has_more=has_more)

    async def count(self, *, filters: list[QueryFilter] | None = None) -> int:
        """A Firestore count aggregation — no documents come back, only the number."""
        query = self.get_client().collection(self._collection_id)

        for filter_ in filters or []:
            query = query.where(filter=FieldFilter(filter_.field, filter_.operator, filter_.value))

        aggregation_results = await query.count(alias="count").get()  # type: ignore
        return int(cast(float, aggregation_results[0][0].value))

    async def query_ids(
        self,
        *,
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: UOW | None = None,
    ) -> list[DocumentID]:
        query = self.client_for_uow(uow).collection(self._collection_id)

        for filter_ in filters or []:
            query = query.where(filter=FieldFilter(filter_.field, filter_.operator, filter_.value))

        if cursor is not None:
            for field in cursor:
                query = query.order_by(field)
            query = query.start_after(cursor)

        if limit is not None:
            query = query.limit(limit)

        if sort_by is not None:
            query = query.order_by(sort_by.field, direction=sort_by.direction)

        raw_entities = await query.get(transaction=uow)  # type: ignore
        entity_ids = [DocumentID(raw_entity.id) for raw_entity in raw_entities]
        return entity_ids

    async def query_one(self, *, filters: list[QueryFilter], uow: UOW | None = None) -> EntityT | None:
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
        return (await self.get_client().collection(self._collection_id).document(document_id).get()).exists

    async def __read_committed_subcollection_metadata(
        self, *, document_id: DocumentID, subentity_names: list[str]
    ) -> dict[str, list[str]]:
        if len(subentity_names) == 0:
            return {}

        document = self.get_client().collection(self._collection_id).document(document_id)
        snapshot = await document.get(field_paths=["_subcollection_metadata"])  # does not use transaction
        if not snapshot.exists:
            return {}

        return (snapshot.to_dict() or {}).get("_subcollection_metadata", {})
