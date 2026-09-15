import os
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, cast

import aioboto3
import boto3
from botocore.exceptions import ClientError

DEFAULT_REGION = "us-east-1"
DEFAULT_DOCUMENT_TABLE_NAME = "acme-documents"
COLLECTION_INDEX_NAME = "collection-index"

_session: aioboto3.Session | None = None
_account_id: str | None = None


def error_code(error: ClientError, /) -> str:
    failure = cast(dict[str, Any], error.response.get("Error", {}))
    return str(failure.get("Code", ""))


def get_region() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_REGION


def get_endpoint_url() -> str | None:
    return os.getenv("AWS_ENDPOINT_URL") or None


def get_account_id() -> str:
    global _account_id
    if _account_id is None:
        _account_id = os.getenv("AWS_ACCOUNT_ID") or _look_up_account_id()
    return _account_id


def reset_account_id() -> None:
    global _account_id
    _account_id = None


def get_document_table_name() -> str:
    return os.getenv("DYNAMODB_TABLE_NAME") or DEFAULT_DOCUMENT_TABLE_NAME


def scope_resource_name(resource_name: str, /) -> str:
    return os.getenv("FEATURE_ENVIRONMENT", "") + resource_name


def get_presign_endpoint_url() -> str:
    return os.getenv("S3_PRESIGN_ENDPOINT_URL") or f"https://s3.{get_region()}.amazonaws.com"


@asynccontextmanager
async def client(service_name: str, /, *, for_presigning: bool = False) -> AsyncGenerator[Any]:
    keywords: dict[str, Any] = {"region_name": get_region()}
    if for_presigning:
        keywords["endpoint_url"] = get_presign_endpoint_url()
    elif get_endpoint_url() is not None:
        keywords["endpoint_url"] = get_endpoint_url()

    opening = cast(
        AbstractAsyncContextManager[Any],
        _get_session().client(service_name, **keywords),  # pyright: ignore[reportUnknownMemberType]
    )
    async with opening as opened:
        yield opened


def _get_session() -> aioboto3.Session:
    global _session
    if _session is None:
        _session = aioboto3.Session()
    return _session


def _look_up_account_id() -> str:
    keywords: dict[str, Any] = {"region_name": get_region()}
    endpoint_url = get_endpoint_url()
    if endpoint_url is not None:
        keywords["endpoint_url"] = endpoint_url
    sts: Any = boto3.client("sts", **keywords)  # pyright: ignore[reportUnknownMemberType]
    identity = cast(dict[str, Any], sts.get_caller_identity())
    return str(identity["Account"])
