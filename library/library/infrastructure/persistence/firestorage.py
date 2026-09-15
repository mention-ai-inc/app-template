import copy
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal, Self, cast

from pydantic import BaseModel

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
from library.domain.value_objects.core import BlobValueObject, IDValueObject, ModelValueObject, StringValueObject
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.persistence.firestore import UOW, Firestore
from library.infrastructure.persistence.storage import BucketName
from library.providers.gcp.storage import ServiceBucket


@dataclass
class ExtractedBlob:
    filepath: str
    data: bytes


class FireStorage[EntityT: IEntity[Any], PartitionKeyT: IDValueObject | StringValueObject]:
    def __init__(
        self,
        *,
        collection: str,
        model: type[EntityT],
        partition_key_type: type[PartitionKeyT],
        service: Service | str | None = None,
        feature_environment: str | None = None,
    ) -> None:
        self._collection = Firestore(
            collection=collection,
            model=model,
            partition_key_type=partition_key_type,
            service=service,
            feature_environment=feature_environment,
        )
        self._model = model
        resolved_service = service if service is not None else os.getenv("SERVICE", "")
        self._service = resolved_service if isinstance(resolved_service, Service) else Service(resolved_service)
        self._storage = ServiceBucket(
            service=self._service, bucket=BucketName.CACHE, feature_environment=feature_environment
        )

    @property
    def collection_id(self) -> str:
        return self._collection.collection_id

    @property
    def active_partition_key(self) -> PartitionKeyT:
        return self._collection.active_partition_key

    @contextmanager
    def connect_to_partition(self, partition_key: PartitionKeyT, /) -> Generator[Self]:
        with self._collection.connect_to_partition(partition_key) as scoped_collection:
            scoped = copy.copy(self)
            scoped._collection = scoped_collection
            yield scoped

    async def get(self, *, document_id: DocumentID, uow: UOW | None = None) -> EntityT:
        raw_entity = await self._collection.get(document_id=document_id, uow=uow)
        entity = await self.__insert_blobs(raw_entity=raw_entity)
        return entity

    async def get_many(
        self, *, document_ids: list[DocumentID], uow: UOW | None = None, ignore_missing: bool = False
    ) -> list[EntityT]:
        raw_entities = await self._collection.get_many(
            document_ids=document_ids, uow=uow, ignore_missing=ignore_missing
        )
        entities = [await self.__insert_blobs(raw_entity=raw_entity) for raw_entity in raw_entities]
        return entities

    async def set(self, *, document_id: DocumentID, document_data: EntityT, uow: UOW | None = None) -> None:
        raw_entity, extracted_blobs = self.__extract_blobs(raw_entity=document_data)
        for extracted_blob in extracted_blobs:
            await self._storage.insert(filepath=extracted_blob.filepath, content=extracted_blob.data)

        await self._collection.set(document_id=document_id, document_data=raw_entity, uow=uow)

    async def update_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate], uow: UOW) -> None:
        await self._collection.update_fields(document_id=document_id, field_updates=field_updates, uow=uow)

    async def field_set(self, *, document_id: DocumentID, field: str, value: Primitive) -> None:
        await self._collection.field_set(document_id=document_id, field=field, value=value)

    async def mutate_fields(self, *, document_id: DocumentID, field_updates: dict[str, FieldUpdate]) -> None:
        await self._collection.mutate_fields(document_id=document_id, field_updates=field_updates)

    async def set_merge(self, *, document_id: DocumentID, document_data: dict[str, Any]) -> None:
        await self._collection.set_merge(document_id=document_id, document_data=document_data)

    async def delete(self, *, document_id: DocumentID, uow: UOW | None = None) -> None:
        paths_to_entity_blobs = await self.__list_entity_blobs(document_id=document_id)
        for path_to_entity_blob in paths_to_entity_blobs:
            await self._storage.delete(filepath=path_to_entity_blob)

        await self._collection.delete(document_id=document_id, uow=uow)

    async def query(
        self,
        *,
        mode: Literal["shallow", "deep"] = "shallow",
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        load_blobs: bool = False,
        uow: UOW | None = None,
    ) -> QueryResult[EntityT]:
        documents = await self._collection.query(
            mode=mode, filters=filters, cursor=cursor, limit=limit, sort_by=sort_by, uow=uow
        )

        if not load_blobs:
            return documents

        return QueryResult(
            entities=[await self.__insert_blobs(raw_entity=document) for document in documents.entities],
            subcollection_counts=documents.subcollection_counts,
            has_more=documents.has_more,
        )

    async def query_ids(
        self,
        *,
        filters: list[QueryFilter] | None = None,
        cursor: dict[str, Primitive] | None = None,
        limit: int | None = None,
        sort_by: SortBy | None = None,
        uow: UOW | None = None,
    ) -> list[DocumentID]:
        return await self._collection.query_ids(filters=filters, cursor=cursor, limit=limit, sort_by=sort_by, uow=uow)

    async def query_one(self, *, filters: list[QueryFilter], uow: UOW | None = None) -> EntityT | None:
        results = await self.query(filters=filters, load_blobs=True, uow=uow)

        if len(results.entities) == 0:
            return None

        if len(results.entities) > 1:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.VALIDATION_ERROR,
                message="Multiple entities found for a query_one",
                public_message="Multiple resources were found",
            )

        return results.entities[0]

    async def count(self, *, filters: list[QueryFilter] | None = None) -> int:
        return await self._collection.count(filters=filters)

    @classmethod
    def to_document_id(cls, entity_id: str | int | ModelValueObject, /) -> DocumentID:
        return Firestore.to_document_id(entity_id)

    async def exists(self, *, document_id: DocumentID) -> bool:
        return await self._collection.exists(document_id=document_id)

    async def __insert_blobs(self, *, raw_entity: EntityT) -> EntityT:
        organization_id = cast(OrganizationID, self._collection.active_partition_key)
        document_id = str(raw_entity.id)

        async def _recursive(value: Any, /) -> Any:
            if isinstance(value, list):
                return [await _recursive(subvalue) for subvalue in value]
            elif isinstance(value, dict):
                return {subkey: await _recursive(subvalue) for subkey, subvalue in value.items()}
            elif isinstance(value, bytes) and value.startswith(BlobValueObject.PLACEHOLDER_PREFIX):
                value_id = value.removeprefix(BlobValueObject.PLACEHOLDER_PREFIX).decode()
                decoded_value = await self.__read_blob_with_legacy_fallback(
                    organization_id=organization_id, document_id=document_id, field_id=value_id
                )
                return decoded_value
            else:
                return value

        inserted_dump = await _recursive(raw_entity.model_dump())
        return self._model.model_validate(inserted_dump)

    def __extract_blobs(self, *, raw_entity: EntityT) -> tuple[EntityT, list[ExtractedBlob]]:
        organization_id = cast(OrganizationID, self._collection.active_partition_key)
        document_id = str(raw_entity.id)
        extracted_blobs: list[ExtractedBlob] = []

        def _recursive[T](*, name: str, value: T) -> T:
            if isinstance(value, list):
                return [_recursive(name=name, value=subvalue) for subvalue in value]  # type: ignore
            elif isinstance(value, BaseModel):
                return type(value).model_validate(
                    {
                        field_name: _recursive(name=field_name, value=getattr(value, field_name))
                        for field_name in type(value).model_fields
                    }
                )
            elif isinstance(value, BlobValueObject):
                filepath = self._storage.get_path_to_blob(
                    organization_id=organization_id, document_id=document_id, field_id=name
                )
                extracted_blob = ExtractedBlob(filepath=filepath, data=value)
                extracted_blobs.append(extracted_blob)
                return type(value)(BlobValueObject.PLACEHOLDER_PREFIX + name.encode())
            else:
                return value

        raw_entity = _recursive(name="", value=raw_entity)
        return raw_entity, extracted_blobs

    async def __list_entity_blobs(self, *, document_id: DocumentID) -> list[str]:
        organization_id = cast(OrganizationID, self._collection.active_partition_key)
        parent_path = f"{self._storage.org_prefix(organization_id)}blobs/{document_id}/"
        new_blobs = await self._storage.list(prefix=parent_path)
        legacy_parent_path = f"blobs/{document_id}/"
        legacy_blobs = await self._storage.list(prefix=legacy_parent_path)
        return new_blobs + legacy_blobs

    async def __read_blob_with_legacy_fallback(
        self, *, organization_id: OrganizationID, document_id: str, field_id: str
    ) -> bytes:
        new_path = self._storage.get_path_to_blob(
            organization_id=organization_id, document_id=document_id, field_id=field_id
        )
        try:
            return await self._storage.get(filepath=new_path)
        except InfrastructureError as error:
            if error.error_type is not InfrastructureErrorType.CLOUD_ERROR:
                raise
            legacy_path = self._storage.get_legacy_path_to_blob(document_id=document_id, field_id=field_id)
            return await self._storage.get(filepath=legacy_path)
