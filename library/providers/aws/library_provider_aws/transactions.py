from dataclasses import dataclass, field
from typing import Literal

from library_provider_aws.serialization import AttributeValue

type DocumentKey = tuple[str, str]

VERSION_ATTRIBUTE = "_version"
COLLECTION_ATTRIBUTE = "_collection"
DOCUMENT_ID_ATTRIBUTE = "_document_id"
SUBCOLLECTION_METADATA_ATTRIBUTE = "_subcollection_metadata"
PARTITION_KEY_ATTRIBUTE = "pk"
SORT_KEY_ATTRIBUTE = "sk"
ROOT_SORT_KEY = "root"
SUBDOCUMENT_SORT_KEY_PREFIX = "sub#"
COMMIT_ITEM_LIMIT = 100


@dataclass
class BufferedWrite:
    key: DocumentKey
    operation: Literal["put", "delete", "update"]
    item: dict[str, AttributeValue] | None = None
    update_expression: str | None = None
    attribute_names: dict[str, str] | None = None
    attribute_values: dict[str, AttributeValue] | None = None


@dataclass
class AwsTransaction:
    writes: list[BufferedWrite] = field(default_factory=list[BufferedWrite])
    read_versions: dict[DocumentKey, int] = field(default_factory=dict[DocumentKey, int])
    has_written: bool = False

    def record_read(self, key: DocumentKey, version: int, /) -> None:
        self.read_versions.setdefault(key, version)

    def buffer(self, write: BufferedWrite, /) -> None:
        self.has_written = True
        self.writes.append(write)


def subdocument_sort_key(*, subentity_name: str, subdocument_id: str) -> str:
    return f"{SUBDOCUMENT_SORT_KEY_PREFIX}{subentity_name}#{subdocument_id}"


def partition_key(*, collection_id: str, document_id: str) -> str:
    return f"{collection_id}#{document_id}"
