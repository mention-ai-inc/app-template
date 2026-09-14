import copy
from dataclasses import dataclass, field
from typing import Any, Literal

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.documents import ArrayRemove, ArrayUnion, FieldUpdate, Increment


@dataclass
class StoredDocument:
    data: dict[str, Any]
    version: int


@dataclass
class BufferedWrite:
    collection_id: str
    document_id: str
    operation: Literal["set", "delete", "update"]
    payload: dict[str, Any] | None


@dataclass
class LocalTransaction:
    writes: list[BufferedWrite] = field(default_factory=list[BufferedWrite])
    read_versions: dict[tuple[str, str], int] = field(default_factory=dict[tuple[str, str], int])
    has_written: bool = False


def apply_field_updates(document: dict[str, Any], field_updates: dict[str, FieldUpdate], /) -> dict[str, Any]:
    updated = copy.deepcopy(document)
    for name, update in field_updates.items():
        if isinstance(update, Increment):
            updated[name] = _as_number(updated.get(name, 0)) + update.value
        elif isinstance(update, ArrayUnion):
            existing = list(updated.get(name, []))
            updated[name] = existing + [value for value in update.values if value not in existing]
        elif isinstance(update, ArrayRemove):
            existing = list(updated.get(name, []))
            updated[name] = [value for value in existing if value not in update.values]
        else:
            updated[name] = update
    return updated


class LocalDatabase:
    _collections: dict[str, dict[str, StoredDocument]] = {}

    @classmethod
    def read(cls, *, collection_id: str, document_id: str) -> StoredDocument | None:
        return cls._collections.get(collection_id, {}).get(document_id)

    @classmethod
    def read_all(cls, *, collection_id: str) -> dict[str, StoredDocument]:
        return cls._collections.get(collection_id, {})

    @classmethod
    def write(cls, *, collection_id: str, document_id: str, data: dict[str, Any]) -> None:
        collection = cls._collections.setdefault(collection_id, {})
        previous = collection.get(document_id)
        collection[document_id] = StoredDocument(
            data=copy.deepcopy(data), version=1 if previous is None else previous.version + 1
        )

    @classmethod
    def remove(cls, *, collection_id: str, document_id: str) -> None:
        cls._collections.get(collection_id, {}).pop(document_id, None)

    @classmethod
    def commit(cls, transaction: LocalTransaction, /) -> None:
        for (collection_id, document_id), read_version in transaction.read_versions.items():
            stored = cls.read(collection_id=collection_id, document_id=document_id)
            current_version = 0 if stored is None else stored.version
            if current_version != read_version:
                raise ApplicationError(
                    error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
                    message=(
                        f"{collection_id}/{document_id} changed during the transaction "
                        f"(read version {read_version}, now {current_version})"
                    ),
                    public_message="Error connecting to the database. Probably temporary! Please try again.",
                )

        for buffered in transaction.writes:
            if buffered.operation == "delete":
                cls.remove(collection_id=buffered.collection_id, document_id=buffered.document_id)
            elif buffered.operation == "set":
                cls.write(
                    collection_id=buffered.collection_id,
                    document_id=buffered.document_id,
                    data=buffered.payload or {},
                )
            else:
                stored = cls.read(collection_id=buffered.collection_id, document_id=buffered.document_id)
                cls.write(
                    collection_id=buffered.collection_id,
                    document_id=buffered.document_id,
                    data=apply_field_updates({} if stored is None else stored.data, buffered.payload or {}),
                )

    @classmethod
    def clear(cls) -> None:
        cls._collections = {}


def _as_number(value: Any, /) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return value
