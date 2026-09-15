from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from azure.cosmos.exceptions import CosmosBatchOperationError, CosmosHttpResponseError

from library.application.errors import ApplicationError, ApplicationErrorType
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.clients import AzureClients
from library_provider_azure.transactions import MAX_BATCH_OPERATIONS, BatchOperation, CosmosTransaction

CONTENDED_STATUS_CODES = frozenset({409, 412, 449})
_transaction: ContextVar[CosmosTransaction | None] = ContextVar("azure_transaction", default=None)


@asynccontextmanager
async def azure_unit_of_work() -> AsyncGenerator[None]:
    token = _transaction.set(CosmosTransaction())
    try:
        yield
        transaction = _transaction.get()
        if transaction is not None:
            await commit(transaction)
    finally:
        _transaction.reset(token)


def get_current_azure_transaction() -> CosmosTransaction:
    transaction = _transaction.get()
    if transaction is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR, message="Unit of work not initialized"
        )
    return transaction


async def commit(transaction: CosmosTransaction, /) -> None:
    writes = transaction.collapsed_writes()
    if len(writes) == 0:
        return

    partitions = transaction.logical_partitions()
    if len(partitions) > 1:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.CLOUD_ERROR,
            message=(
                "A Cosmos DB transactional batch is one container and one logical partition, but this unit of "
                f"work writes to {sorted(partitions)}. Give every document in the block the same partition value "
                "(see .agents/rules/read-after-write.md for how a unit of work is meant to be shaped)."
            ),
        )

    if len(writes) > MAX_BATCH_OPERATIONS:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.CLOUD_ERROR,
            message=(
                f"A Cosmos DB transactional batch holds at most {MAX_BATCH_OPERATIONS} operations, "
                f"but this unit of work buffered {len(writes)}"
            ),
        )

    container_name, partition_value = writes[0].container_name, writes[0].partition_value
    operations: list[BatchOperation] = [buffered.to_batch_operation() for buffered in writes]

    try:
        await AzureClients.container(container_name).execute_item_batch(
            batch_operations=operations, partition_key=partition_value
        )
    except CosmosBatchOperationError as error:
        raise __as_commit_error(status_code=error.status_code, error=error) from error
    except CosmosHttpResponseError as error:
        raise __as_commit_error(status_code=error.status_code, error=error) from error


def __as_commit_error(*, status_code: int | None, error: Exception) -> Exception:
    if status_code in CONTENDED_STATUS_CODES:
        return ApplicationError(
            error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
            message=f"There was contention on a resource in the database: {error}",
            public_message="Error connecting to the database. Probably temporary! Please try again.",
        )
    if status_code == 429:
        return ApplicationError(
            error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
            message=f"Cosmos DB throttled the transactional batch: {error}",
            public_message="Error connecting to the database. Probably temporary! Please try again.",
        )
    return InfrastructureError(
        error_type=InfrastructureErrorType.CLOUD_ERROR,
        message=f"Cosmos DB rejected the transactional batch: {error}",
        public_message="The database rejected the request. Please try again later.",
    )
