from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.providers.local.database import LocalDatabase, LocalTransaction

_transaction: ContextVar[LocalTransaction | None] = ContextVar("local_transaction", default=None)


@asynccontextmanager
async def local_unit_of_work() -> AsyncGenerator[None]:
    token = _transaction.set(LocalTransaction())
    try:
        yield
        transaction = _transaction.get()
        if transaction is not None:
            LocalDatabase.commit(transaction)
    finally:
        _transaction.reset(token)


def get_current_local_transaction() -> LocalTransaction:
    transaction = _transaction.get()
    if transaction is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR, message="Unit of work not initialized"
        )
    return transaction
