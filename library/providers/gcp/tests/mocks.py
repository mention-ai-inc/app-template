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


def make_doc_snapshot(*, data: dict[str, Any], doc_id: str) -> MagicMock:
    """A fake `DocumentSnapshot` with `.to_dict`, `.id`, `.reference`."""
    doc = MagicMock()
    doc.to_dict.return_value = data
    doc.id = doc_id
    return doc


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
        "library_provider_gcp.firestore.Firestore.get_client",
        return_value=mock_client,
    )
    return mock_client


def make_mock_transaction() -> AsyncMock:
    """A fake async transaction. `_clean_up` is sync; `_begin`/`_rollback` are async.

    `unit_of_work` commits via the client's gapic `commit` (with `retry=None`) rather
    than `transaction._commit()`, so the client internals it touches are wired up here.
    """
    transaction = AsyncMock()
    transaction._clean_up = MagicMock()
    transaction._begin = AsyncMock()
    transaction._rollback = AsyncMock()
    transaction.in_progress = True
    transaction._id = b"txn-id"
    transaction._write_pbs = []
    transaction._client = MagicMock()
    transaction._client._database_string = "projects/test/databases/(default)"
    transaction._client._rpc_metadata = []
    transaction._client._firestore_api.commit = AsyncMock()
    return transaction


def patch_firestore_transaction(mocker: MockerFixture) -> AsyncMock:
    """Patch `Firestore.get_client()` so each `gcp_unit_of_work` call gets the same mock transaction."""
    transaction = make_mock_transaction()
    mock_client = MagicMock()
    mock_client.transaction.return_value = transaction
    mocker.patch(
        "library_provider_gcp.unit_of_work.Firestore.get_client",
        return_value=mock_client,
    )
    return transaction


def patch_firestore_transactions(mocker: MockerFixture, *, count: int) -> list[AsyncMock]:
    """Patch `Firestore.get_client()` so successive `.transaction()` calls yield distinct mocks."""
    transactions = [make_mock_transaction() for _ in range(count)]
    mock_client = MagicMock()
    mock_client.transaction.side_effect = transactions
    mocker.patch(
        "library_provider_gcp.unit_of_work.Firestore.get_client",
        return_value=mock_client,
    )
    return transactions
