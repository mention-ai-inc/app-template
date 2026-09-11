from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from google.api_core.exceptions import Aborted, DeadlineExceeded, InvalidArgument, ServiceUnavailable

from library.application.errors import ApplicationError, ApplicationErrorType
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.persistence.firestore import UOW, Firestore

_uow: ContextVar[UOW | None] = ContextVar("uow", default=None)


@asynccontextmanager
async def unit_of_work() -> AsyncGenerator[None]:
    transaction = Firestore.get_client().transaction()
    old_uow = _uow.get()
    try:
        transaction._clean_up()  # pyright: ignore[reportPrivateUsage]
        await transaction._begin()  # pyright: ignore[reportPrivateUsage]
        uow = UOW(transaction)
        _uow.set(uow)
        yield
        await _commit_once(uow)
    except Exception as error:
        if transaction.in_progress:
            try:
                await transaction._rollback()  # pyright: ignore[reportPrivateUsage]
            except Exception:
                pass
        if isinstance(error, (Aborted, ServiceUnavailable, DeadlineExceeded)):
            raise ApplicationError(
                error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
                message=f"There was contention on a resource in the database: {error}",
                public_message="Error connecting to the database. Probably temporary! Please try again.",
            ) from error
        if isinstance(error, InvalidArgument):
            if __is_transient_transaction_error(error):
                raise ApplicationError(
                    error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
                    message=f"The database transaction was no longer valid: {error}",
                    public_message="Error connecting to the database. Probably temporary! Please try again.",
                ) from error
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"Firestore rejected the transaction as invalid: {error}",
                public_message="The database rejected the request. Please try again later.",
            ) from error
        raise error
    finally:
        _uow.set(old_uow)


def get_current_uow() -> UOW:
    uow = _uow.get()
    if uow is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR, message="Unit of work not initialized"
        )

    return uow


async def _commit_once(transaction: UOW) -> None:
    client = transaction._client  # pyright: ignore[reportPrivateUsage]
    await client._firestore_api.commit(  # pyright: ignore[reportPrivateUsage]
        request={
            "database": client._database_string,  # pyright: ignore[reportPrivateUsage]
            "writes": transaction._write_pbs,  # pyright: ignore[reportPrivateUsage]
            "transaction": transaction._id,  # pyright: ignore[reportPrivateUsage]
        },
        metadata=client._rpc_metadata,  # pyright: ignore[reportPrivateUsage]
        retry=None,
    )
    transaction._clean_up()  # pyright: ignore[reportPrivateUsage]


def __is_transient_transaction_error(error: InvalidArgument) -> bool:
    message = str(error).lower()
    return "transaction" in message and ("expired" in message or "no longer valid" in message)
