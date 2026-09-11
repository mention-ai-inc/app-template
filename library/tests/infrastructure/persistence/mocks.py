from typing import Any
from unittest.mock import AsyncMock, MagicMock

from pytest_mock import MockerFixture

from library.domain.entities import Entity
from library.domain.value_objects.core import (
    IDValueObject,
    IntegerValueObject,
    ModelValueObject,
)


class MainId(IDValueObject):
    PREFIX = "main_"


class StringSubId(IDValueObject):
    PREFIX = "ssub_"


class StringSub(Entity[StringSubId]):
    pass


class IntSubId(IntegerValueObject):
    pass


class IntSub(Entity[IntSubId]):
    pass


class CompositeSubId(ModelValueObject):
    org: str
    user: str


class CompositeSub(Entity[CompositeSubId]):
    pass


class MainEntity(Entity[MainId]):
    string_subs: list[StringSub] = []
    int_subs: list[IntSub] = []
    composite_subs: list[CompositeSub] = []


class SimpleEntity(Entity[MainId]):
    name: str = ""


class MockPartitionKey(IDValueObject):
    PREFIX = "tp_"


def patch_firestore_client(mocker: MockerFixture) -> MagicMock:
    """Patch `Firestore.get_client()` and return the mock client.

    The mock is wired so the chainable query interface (`.where`, `.order_by`,
    `.start_after`, `.limit`) on `client.collection(...)` returns the same
    object, and `.get(...)` is an `AsyncMock` returning `[]` by default.
    Override `mock_client.collection.return_value.get` per test as needed.

    `document(...).get(...)` is an `AsyncMock` resolving to a non-existent
    snapshot, so `set()` sees no previously committed subcollection metadata and
    prunes nothing. Point it at `make_doc_snapshot(...)` to exercise pruning.
    """
    mock_client = MagicMock()
    chainable = mock_client.collection.return_value
    chainable.where.return_value = chainable
    chainable.order_by.return_value = chainable
    chainable.start_after.return_value = chainable
    chainable.limit.return_value = chainable
    chainable.get = AsyncMock(return_value=[])

    missing = make_doc_snapshot(data={}, doc_id="missing")
    missing.exists = False
    chainable.document.return_value.get = AsyncMock(return_value=missing)

    mocker.patch(
        "library.infrastructure.persistence.firestore.Firestore.get_client",
        return_value=mock_client,
    )
    return mock_client


def make_doc_snapshot(*, data: dict[str, Any], doc_id: str) -> MagicMock:
    """A fake `DocumentSnapshot` with `.to_dict`, `.id`, `.reference`."""
    doc = MagicMock()
    doc.to_dict.return_value = data
    doc.id = doc_id
    return doc
