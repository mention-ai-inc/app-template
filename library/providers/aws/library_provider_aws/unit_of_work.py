from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from botocore.exceptions import ClientError

from library.application.errors import ApplicationError, ApplicationErrorType
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_aws.clients import client, error_code, get_document_table_name
from library_provider_aws.serialization import AttributeValue, to_attribute_value
from library_provider_aws.transactions import (
    COMMIT_ITEM_LIMIT,
    PARTITION_KEY_ATTRIBUTE,
    SORT_KEY_ATTRIBUTE,
    VERSION_ATTRIBUTE,
    AwsTransaction,
    BufferedWrite,
    DocumentKey,
)

CONFLICT_PUBLIC_MESSAGE = "Error connecting to the database. Probably temporary! Please try again."
CONTENDED_ERROR_CODES = frozenset(
    {"TransactionCanceledException", "TransactionConflictException", "ConditionalCheckFailedException"}
)

_transaction: ContextVar[AwsTransaction | None] = ContextVar("aws_transaction", default=None)


@asynccontextmanager
async def aws_unit_of_work() -> AsyncGenerator[None]:
    token = _transaction.set(AwsTransaction())
    try:
        yield
        transaction = _transaction.get()
        if transaction is not None:
            await commit(transaction)
    finally:
        _transaction.reset(token)


def get_current_aws_transaction() -> AwsTransaction:
    transaction = _transaction.get()
    if transaction is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR, message="Unit of work not initialized"
        )
    return transaction


async def commit(transaction: AwsTransaction, /) -> None:
    transact_items = __transact_items(transaction)
    if len(transact_items) == 0:
        return

    if len(transact_items) > COMMIT_ITEM_LIMIT:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.CLOUD_ERROR,
            message=(
                f"A unit of work may touch at most {COMMIT_ITEM_LIMIT} documents in one commit, "
                f"and this one touches {len(transact_items)}"
            ),
        )

    async with client("dynamodb") as dynamodb:
        try:
            await dynamodb.transact_write_items(TransactItems=transact_items)
        except ClientError as error:
            if error_code(error) in CONTENDED_ERROR_CODES:
                raise ApplicationError(
                    error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
                    message=f"A document changed during the transaction: {error}",
                    public_message=CONFLICT_PUBLIC_MESSAGE,
                ) from error
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"DynamoDB rejected the transaction: {error}",
                public_message="The database rejected the request. Please try again later.",
            ) from error


def __transact_items(transaction: AwsTransaction, /) -> list[dict[str, Any]]:
    table_name = get_document_table_name()
    latest_by_key: dict[DocumentKey, BufferedWrite] = {}
    for write in transaction.writes:
        latest_by_key[write.key] = write

    transact_items = [
        __transact_item(write, table_name=table_name, expected_version=transaction.read_versions.get(write.key))
        for write in latest_by_key.values()
    ]

    transact_items.extend(
        __condition_check(key, table_name=table_name, expected_version=expected_version)
        for key, expected_version in transaction.read_versions.items()
        if key not in latest_by_key
    )

    return transact_items


def __transact_item(write: BufferedWrite, /, *, table_name: str, expected_version: int | None) -> dict[str, Any]:
    condition = __version_condition(expected_version)

    if write.operation == "put":
        request: dict[str, Any] = {"TableName": table_name, "Item": write.item or {}}
        return {"Put": __with_condition(request, condition)}

    if write.operation == "delete":
        request = {"TableName": table_name, "Key": __key_attributes(write.key)}
        return {"Delete": __with_condition(request, condition)}

    request = {
        "TableName": table_name,
        "Key": __key_attributes(write.key),
        "UpdateExpression": write.update_expression or "",
        "ExpressionAttributeNames": dict(write.attribute_names or {}),
        "ExpressionAttributeValues": dict(write.attribute_values or {}),
    }
    return {"Update": __with_condition(request, condition)}


def __condition_check(key: DocumentKey, /, *, table_name: str, expected_version: int) -> dict[str, Any]:
    request: dict[str, Any] = {"TableName": table_name, "Key": __key_attributes(key)}
    return {"ConditionCheck": __with_condition(request, __version_condition(expected_version))}


def __version_condition(
    expected_version: int | None, /
) -> tuple[str, dict[str, str], dict[str, AttributeValue]] | None:
    if expected_version is None:
        return None
    if expected_version == 0:
        return (f"attribute_not_exists({PARTITION_KEY_ATTRIBUTE})", {}, {})
    return (
        "#expected_version_name = :expected_version",
        {"#expected_version_name": VERSION_ATTRIBUTE},
        {":expected_version": to_attribute_value(expected_version)},
    )


def __with_condition(
    request: dict[str, Any], condition: tuple[str, dict[str, str], dict[str, AttributeValue]] | None, /
) -> dict[str, Any]:
    if condition is None:
        return request

    expression, names, values = condition
    request["ConditionExpression"] = expression
    if len(names) > 0:
        request["ExpressionAttributeNames"] = {**request.get("ExpressionAttributeNames", {}), **names}
    if len(values) > 0:
        request["ExpressionAttributeValues"] = {**request.get("ExpressionAttributeValues", {}), **values}
    return request


def __key_attributes(key: DocumentKey, /) -> dict[str, AttributeValue]:
    return {
        PARTITION_KEY_ATTRIBUTE: to_attribute_value(key[0]),
        SORT_KEY_ATTRIBUTE: to_attribute_value(key[1]),
    }
