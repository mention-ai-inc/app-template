from unittest.mock import AsyncMock, MagicMock

from pytest_mock import MockerFixture


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
    """Patch `Firestore.get_client()` so each `unit_of_work` call gets the same mock transaction."""
    transaction = make_mock_transaction()
    mock_client = MagicMock()
    mock_client.transaction.return_value = transaction
    mocker.patch(
        "library.infrastructure.unit_of_work.Firestore.get_client",
        return_value=mock_client,
    )
    return transaction


def patch_firestore_transactions(mocker: MockerFixture, *, count: int) -> list[AsyncMock]:
    """Patch `Firestore.get_client()` so successive `.transaction()` calls yield distinct mocks."""
    transactions = [make_mock_transaction() for _ in range(count)]
    mock_client = MagicMock()
    mock_client.transaction.side_effect = transactions
    mocker.patch(
        "library.infrastructure.unit_of_work.Firestore.get_client",
        return_value=mock_client,
    )
    return transactions
